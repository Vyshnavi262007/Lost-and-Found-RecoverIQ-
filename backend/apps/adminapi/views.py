import re
from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdminRole, IsStaffRole
from apps.accounts.serializers import UserSerializer, email_domain_allowed
from apps.claims import services as claim_services
from apps.claims.models import Claim, HandoverRecord, InventoryRecord
from apps.claims.services import ClaimError
from apps.claims.views import claim_dict
from apps.core.models import AuditLog, Campus, CampusLocation, ItemCategory, Notification
from apps.core.serializers import AuditLogSerializer, CategorySerializer, LocationSerializer
from apps.core.services import audit, notify
from apps.core.site_settings import all_settings, validate_setting
from apps.reports import matching
from apps.reports.matching_service import features, recompute_matches
from apps.reports.models import AbuseReport, Comment, ItemReport, Match
from apps.reports.queries import annotated
from apps.reports.serializers import ReportListSerializer


class AdminUserSerializer(UserSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["is_active", "last_login"]


class UserList(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = User.objects.all().order_by("-date_joined")
        p = request.query_params
        if p.get("q"):
            qs = qs.filter(Q(email__icontains=p["q"]) | Q(first_name__icontains=p["q"]) | Q(last_name__icontains=p["q"])
                           | Q(student_id__icontains=p["q"]))
        if p.get("role"):
            qs = qs.filter(role=p["role"])
        if p.get("active") in ("0", "1"):
            qs = qs.filter(is_active=p["active"] == "1")
        pag = PageNumberPagination()
        pag.page_size = 20
        page = pag.paginate_queryset(qs, request)
        return pag.get_paginated_response(AdminUserSerializer(page, many=True).data)

    def post(self, request):
        """Create a staff/admin/student account (pre-verified, approved by the creating admin)."""
        d = request.data
        email = (d.get("email") or "").strip().lower()
        errors = {}
        if not email_domain_allowed(email):
            errors["email"] = "Email must use an allowed college domain."
        elif User.objects.filter(email__iexact=email).exists():
            errors["email"] = "Email already in use."
        role = d.get("role", "staff")
        if role not in ("student", "faculty", "staff", "admin"):
            errors["role"] = "Invalid role."
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(d.get("password") or "")
        except ValidationError as e:
            errors["password"] = list(e.messages)
        if errors:
            return Response(errors, status=400)
        parts = (d.get("full_name") or email.split("@")[0]).split(" ", 1)
        u = User(username=email, email=email, first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
                 role=role, email_verified=True, staff_title=(d.get("staff_title") or "")[:80],
                 can_review_claims=bool(d.get("can_review_claims")), can_release_items=bool(d.get("can_release_items")))
        u.set_password(d["password"])
        u.save()
        audit(request.user, "admin.user_created", u, {"role": role}, request)
        return Response(AdminUserSerializer(u).data, status=201)


class UserDetail(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        u = User.objects.filter(pk=pk).first()
        if not u:
            return Response(status=404)
        d, changed = request.data, {}
        if u.pk == request.user.pk and (d.get("is_active") is False or (d.get("role") and d["role"] != "admin")):
            return Response({"detail": "You cannot deactivate or demote your own account."}, status=400)
        for f in ("is_active", "email_verified", "can_review_claims", "can_release_items"):
            if f in d:
                setattr(u, f, bool(d[f]))
                changed[f] = bool(d[f])
        if "role" in d:
            if d["role"] not in ("student", "faculty", "staff", "admin"):
                return Response({"role": ["Invalid role."]}, status=400)
            u.role = d["role"]
            changed["role"] = d["role"]
            u.staff_requested = False
        if "staff_title" in d:
            u.staff_title = str(d["staff_title"])[:80]
        u.save()
        audit(request.user, "admin.user_updated", u, changed, request)
        return Response(AdminUserSerializer(u).data)


class StaffRequests(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = User.objects.filter(staff_requested=True, role__in=["student", "faculty"], is_active=True, email_verified=True)
        return Response(AdminUserSerializer(qs, many=True).data)

    def post(self, request, pk):
        u = User.objects.filter(pk=pk, staff_requested=True, role__in=["student", "faculty"]).first()
        if not u:
            return Response({"detail": "Request not found."}, status=404)
        if request.data.get("decision") == "approve":
            u.role, u.staff_requested = (u.requested_role if u.requested_role in ("staff", "admin") else "staff"), False
            u.requested_role = ""
            u.can_review_claims = bool(request.data.get("can_review_claims", True))
            u.can_release_items = bool(request.data.get("can_release_items", False))
            u.staff_title = str(request.data.get("staff_title", ""))[:80]
            u.save()
            audit(request.user, "admin.staff_approved", u, request=request)
            notify(u, "system", "Your staff access was approved", "Sign in again to see staff tools.", "/")
        else:
            u.staff_requested, u.requested_role = False, ""
            u.save(update_fields=["staff_requested", "requested_role"])
            audit(request.user, "admin.staff_rejected", u, request=request)
        return Response(AdminUserSerializer(u).data)


class ModerationReports(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = annotated(ItemReport.objects.all(), request.user)
        p = request.query_params
        if p.get("moderation"):
            qs = qs.filter(moderation=p["moderation"])
        if p.get("q"):
            qs = qs.filter(Q(title__icontains=p["q"]) | Q(description__icontains=p["q"]))
        qs = qs.order_by("-created_at")
        pag = PageNumberPagination()
        pag.page_size = 15
        page = pag.paginate_queryset(qs, request)
        return pag.get_paginated_response(ReportListSerializer(page, many=True, context={"request": request}).data)

    def post(self, request, pk):
        r = ItemReport.objects.filter(pk=pk).first()
        if not r:
            return Response(status=404)
        value = request.data.get("moderation")
        if value not in ("approved", "pending", "removed"):
            return Response({"moderation": ["Invalid value."]}, status=400)
        r.moderation = value
        r.save(update_fields=["moderation", "updated_at"])
        audit(request.user, f"report.moderation_{value}", r, {"reason": str(request.data.get("reason", ""))[:300]}, request)
        if value == "removed":
            notify(r.reporter, "status", "A moderator removed your report", r.title, "/my-reports")
        recompute_matches(r)
        return Response({"moderation": value})


class AbuseList(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = AbuseReport.objects.select_related("reporter", "report", "comment__report")
        qs = qs.filter(status=request.query_params.get("status", "open"))
        out = []
        for a in qs:
            report = a.report or (a.comment.report if a.comment else None)
            out.append({"id": a.id, "reason": a.get_reason_display(), "details": a.details, "status": a.status,
                        "created_at": a.created_at, "reporter": a.reporter.display_name,
                        "report_id": report.id if report else None, "report_title": report.title if report else "",
                        "comment_body": a.comment.body if a.comment else None, "resolution_note": a.resolution_note})
        return Response(out)

    @transaction.atomic
    def post(self, request, pk):
        a = AbuseReport.objects.select_related("report", "comment").filter(pk=pk, status="open").first()
        if not a:
            return Response({"detail": "Not found."}, status=404)
        action = request.data.get("action")
        if action not in ("dismiss", "resolve", "remove_content"):
            return Response({"action": ["dismiss, resolve or remove_content"]}, status=400)
        if action == "remove_content":
            if a.comment:
                a.comment.is_removed = True
                a.comment.save(update_fields=["is_removed"])
            elif a.report:
                a.report.moderation = "removed"
                a.report.save(update_fields=["moderation", "updated_at"])
        a.status = "dismissed" if action == "dismiss" else "resolved"
        a.resolution_note = str(request.data.get("note", ""))[:500]
        a.resolved_by, a.resolved_at = request.user, timezone.now()
        a.save()
        audit(request.user, f"abuse.{action}", a, request=request)
        return Response({"status": a.status})


class Duplicates(APIView):
    """Likely duplicate reports: same reporter + same type + very similar text, computed on the fly."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        reports = list(ItemReport.objects.filter(status="open", moderation="approved")
                       .select_related("category", "location", "reporter").order_by("-created_at")[:300])
        by_key = {}
        for r in reports:
            by_key.setdefault((r.reporter_id, r.type, r.category_id), []).append(r)
        pairs = []
        for group in by_key.values():
            for i, a in enumerate(group):
                rest = group[i + 1:]
                if not rest:
                    continue
                sims = matching.text_similarities(features(a)["text"], [features(b)["text"] for b in rest])
                for b, s in zip(rest, sims):
                    if s is not None and s >= 0.6:
                        pairs.append({"similarity": round(s, 2),
                                      "a": {"id": a.id, "title": a.title, "date": a.date},
                                      "b": {"id": b.id, "title": b.title, "date": b.date},
                                      "reporter": a.reporter.display_name})
        return Response(sorted(pairs, key=lambda p: -p["similarity"])[:50])


class Disputes(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = Claim.objects.filter(dispute_status=request.query_params.get("dispute", "open")).select_related(
            "report__location", "claimant", "reviewer")
        return Response([claim_dict(c, request.user, request) | {"dispute_note": c.dispute_note,
                                                                 "dispute_resolution": c.dispute_resolution}
                         for c in qs])

    def post(self, request, pk):
        try:
            claim_services.resolve_dispute(request.user, pk, request.data.get("outcome"), request.data.get("note"))
        except ClaimError as e:
            return Response({"detail": e.message}, status=e.status)
        return Response({"detail": "Dispute resolved."})


class CrudMixin:
    permission_classes = [IsAdminRole]
    pagination_class = None
    audit_name = ""

    def perform_create(self, serializer):
        obj = serializer.save()
        audit(self.request.user, f"{self.audit_name}.created", obj, request=self.request)

    def perform_update(self, serializer):
        obj = serializer.save()
        audit(self.request.user, f"{self.audit_name}.updated", obj, request=self.request)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        try:
            obj.delete()
        except ProtectedError:
            return Response({"detail": "In use by existing reports. Deactivate it instead."}, status=409)
        audit(request.user, f"{self.audit_name}.deleted", None, {"id": kwargs.get("pk")}, request)
        return Response(status=204)


class CategoryViewSet(CrudMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = ItemCategory.objects.all()
    audit_name = "category"

    def perform_create(self, serializer):
        name = serializer.validated_data["name"]
        obj = serializer.save(slug=slugify(name) or "category")
        audit(self.request.user, "category.created", obj, request=self.request)


class LocationViewSet(CrudMixin, viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    queryset = CampusLocation.objects.select_related("campus").all()
    audit_name = "location"


class AuditLogList(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = AuditLog.objects.select_related("actor")
        p = request.query_params
        if p.get("action"):
            qs = qs.filter(action__icontains=p["action"])
        if p.get("q"):
            qs = qs.filter(Q(actor__email__icontains=p["q"]) | Q(target_type__icontains=p["q"]))
        pag = PageNumberPagination()
        pag.page_size = 25
        page = pag.paginate_queryset(qs, request)
        return pag.get_paginated_response(AuditLogSerializer(page, many=True).data)


class SettingsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(all_settings())

    def patch(self, request):
        from apps.core.models import SiteSetting
        errors, cleaned = {}, {}
        for k, v in request.data.items():
            try:
                cleaned[k] = validate_setting(k, v)
            except (ValueError, TypeError) as e:
                errors[k] = str(e)
        if errors:
            return Response(errors, status=400)
        for k, v in cleaned.items():
            SiteSetting.objects.update_or_create(key=k, defaults={"value": v})
        audit(request.user, "settings.updated", None, cleaned, request)
        return Response(all_settings())


class Analytics(APIView):
    """All figures are aggregated from the database. Definitions are returned with the numbers."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            days = 30
        since = timezone.now() - timedelta(days=days) if days > 0 else None
        reports = ItemReport.objects.exclude(moderation="removed")
        scoped = reports.filter(created_at__gte=since) if since else reports
        found = scoped.filter(type="found")
        returned = found.filter(status="returned", returned_at__isnull=False)
        durations = [(r - c).total_seconds() / 3600 for c, r in returned.values_list("created_at", "returned_at")]
        found_total = found.count()
        by_day = {}
        for row in scoped.annotate(d=TruncDate("created_at")).values("d", "type").annotate(n=Count("id")):
            by_day.setdefault(str(row["d"]), {"date": str(row["d"]), "lost": 0, "found": 0})[row["type"]] = row["n"]
        data = {
            "days": days,
            "totals": {
                "users": User.objects.count(),
                "active_students": User.objects.filter(role="student", is_active=True).count(),
                "active_faculty": User.objects.filter(role="faculty", is_active=True).count(),
                "active_staff": User.objects.filter(role="staff", is_active=True).count(),
                "lost_reports": scoped.filter(type="lost").count(),
                "found_reports": found_total,
                "open_reports": scoped.filter(status="open").count(),
                "possible_matches": Match.objects.filter(status="new").count(),
                "pending_claims": Claim.objects.filter(status__in=["pending", "under_review"]).count(),
                "items_returned": returned.count(),
                "recovery_rate": round(returned.count() / found_total, 3) if found_total else None,
                "avg_hours_to_recovery": round(sum(durations) / len(durations), 1) if durations else None,
                "open_disputes": Claim.objects.filter(dispute_status="open").count(),
                "open_abuse_reports": AbuseReport.objects.filter(status="open").count(),
                "inventory_in_storage": InventoryRecord.objects.filter(status="stored").count(),
            },
            "reports_by_day": sorted(by_day.values(), key=lambda r: r["date"]),
            "top_categories": list(scoped.values(name=F("category__name"))
                                   .annotate(count=Count("id")).order_by("-count")[:8]),
            "top_locations": list(scoped.values(name=F("location__name"))
                                  .annotate(count=Count("id")).order_by("-count")[:8]),
            "recent_audit": AuditLogSerializer(AuditLog.objects.select_related("actor")[:8], many=True).data,
            "definitions": {
                "recovery_rate": "Found-item reports (in the period) that were returned, divided by all found-item reports in the period.",
                "avg_hours_to_recovery": "Average hours from a found report's creation to its confirmed return.",
            },
        }
        return Response(data)


class StudentDashboard(APIView):
    def get(self, request):
        u = request.user
        mine = ItemReport.objects.filter(reporter=u)
        from apps.core.serializers import NotificationSerializer
        recent = annotated(ItemReport.objects.filter(moderation="approved", status="open"), u).order_by("-created_at")[:6]
        return Response({
            "active_reports": mine.filter(status="open").count(),
            "possible_matches": Match.objects.filter(status="new").filter(
                Q(lost_report__reporter=u, lost_report__status="open") | Q(found_report__reporter=u, found_report__status="open")
            ).count(),
            "pending_claims": Claim.objects.filter(claimant=u, status__in=["pending", "under_review", "approved"]).count(),
            "items_recovered": Claim.objects.filter(claimant=u, status="completed").count(),
            "recent_notifications": NotificationSerializer(Notification.objects.filter(user=u)[:5], many=True).data,
            "recent_reports": ReportListSerializer(recent, many=True, context={"request": request}).data,
        })


class StaffDashboard(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        month = timezone.now() - timedelta(days=30)
        pending = [c for c in Claim.objects.filter(status__in=["pending", "under_review"]).select_related("report")
                   if claim_services.can_review_claim(request.user, c)]
        return Response({
            "items_in_storage": InventoryRecord.objects.filter(status="stored").count(),
            "claims_to_review": len(pending),
            "approved_awaiting_handover": Claim.objects.filter(status="approved", report__held_by_staff=True).exclude(
                handovers__status="scheduled").count(),
            "scheduled_handovers": HandoverRecord.objects.filter(status="scheduled").count(),
            "returned_last_30_days": HandoverRecord.objects.filter(status="completed", confirmed_at__gte=month).count(),
            "can_release_items": request.user.role == "admin" or request.user.can_release_items,
        })
