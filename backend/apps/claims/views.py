import mimetypes
from datetime import datetime

from django.http import FileResponse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffRole, can_release
from apps.core.pagination import StandardPagination
from apps.core.services import audit
from apps.reports.models import ItemReport
from apps.reports.serializers import thumbnail
from apps.reports.views import create_report

from . import services
from .models import Claim, ClaimEvidence, HandoverRecord, InventoryRecord
from .services import ClaimError, can_review_claim, can_view_claim

QUESTIONS = ["Describe any unique marks, scratches, stickers or damage.",
             "What is inside, attached to, or stored on the item?",
             "Where and roughly when did you lose it?"]
MAX_EVIDENCE = 5 * 1024 * 1024


def handover_dict(h):
    return {"id": h.id, "reference": h.reference, "scheduled_for": h.scheduled_for, "location": h.location,
            "notes": h.notes, "status": h.status, "claim_id": h.claim_id,
            "item": h.claim.report.title if h.claim_id else "",
            "confirmed_by": h.confirmed_by.display_name if h.confirmed_by else None, "confirmed_at": h.confirmed_at,
            "scheduled_by": h.scheduled_by.display_name, "inventory_reference": h.inventory.reference if h.inventory else None}


def claim_dict(claim, user, request, detail=True):
    report = claim.report
    reviewer_view = can_review_claim(user, claim)
    privileged = reviewer_view or user.role in ("staff", "admin")
    claimant = claim.claimant
    data = {
        "id": claim.id, "status": claim.status, "status_display": claim.get_status_display(),
        "created_at": claim.created_at, "updated_at": claim.updated_at,
        "report": {"id": report.id, "title": report.title, "type": report.type, "status": report.status,
                   "held_by_staff": report.held_by_staff, "location": report.location.name,
                   "thumbnail": thumbnail(report, request)},
        "claimant_name": claimant.full_name if privileged else claimant.display_name,
        "is_claimant": claim.claimant_id == user.id, "can_review": reviewer_view,
        "decision_reason": claim.decision_reason, "reviewed_at": claim.reviewed_at,
        "reviewer_name": claim.reviewer.display_name if claim.reviewer else None,
        "dispute_status": claim.dispute_status,
    }
    if not detail:
        return data
    data.update({
        "description": claim.description, "answers": claim.answers, "preferred_handover": claim.preferred_handover,
        "claimant_student_id": claimant.student_id if privileged else None,
        "dispute_note": claim.dispute_note, "dispute_resolution": claim.dispute_resolution,
        "events": [{"status": e.status, "note": e.note, "at": e.created_at,
                    "actor": e.actor.display_name if e.actor else "system"} for e in claim.events.select_related("actor")],
        "evidence": [{"id": e.id, "name": e.original_name, "note": e.note, "created_at": e.created_at}
                     for e in claim.evidence.all()],
        "handovers": [handover_dict(h) for h in claim.handovers.select_related("claim__report", "confirmed_by",
                                                                              "scheduled_by", "inventory")],
        # Hidden identifying details are shown ONLY to people allowed to review. Never to the claimant.
        "report_private_details": report.private_details if reviewer_view else None,
        "can_withdraw": claim.claimant_id == user.id and claim.status in services.LIVE,
        "can_dispute": claim.claimant_id == user.id and claim.status == "rejected" and claim.dispute_status == "none",
        "can_add_evidence": claim.claimant_id == user.id and claim.status in ("pending", "under_review"),
        "can_schedule_handover": claim.status == "approved" and report.held_by_staff and can_release(user),
        "can_confirm_return": (claim.status == "approved" and not report.held_by_staff
                               and user.id == report.reporter_id and user.id != claim.claimant_id),
    })
    return data


def _err(e):
    return Response({"detail": e.message}, status=e.status)


class ClaimQuestions(APIView):
    def get(self, request):
        return Response(QUESTIONS)


class ClaimListCreate(APIView):
    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "write"
            return [ScopedRateThrottle()]
        return []

    def get(self, request):
        qs = Claim.objects.select_related("report__location", "report__category", "claimant", "reviewer").prefetch_related(
            "report__images")
        if request.query_params.get("scope") == "review":
            if request.user.role not in ("staff", "admin"):
                qs = qs.filter(report__reporter=request.user, report__held_by_staff=False)
            else:
                qs = qs.exclude(claimant=request.user)
            if request.query_params.get("status"):
                qs = qs.filter(status=request.query_params["status"])
            items = [c for c in qs if can_review_claim(request.user, c)]
        else:
            qs = qs.filter(claimant=request.user)
            if request.query_params.get("status"):
                qs = qs.filter(status=request.query_params["status"])
            items = list(qs)
        pag = StandardPagination()
        page = pag.paginate_queryset(items, request)
        return pag.get_paginated_response([claim_dict(c, request.user, request, detail=False) for c in page])

    def post(self, request):
        try:
            claim = services.submit_claim(request.user, request.data.get("report"), request.data.get("description"),
                                          request.data.get("answers"), request.data.get("preferred_handover", ""))
        except ClaimError as e:
            return _err(e)
        return Response(claim_dict(claim, request.user, request), status=201)


class ClaimDetail(APIView):
    def get(self, request, pk):
        claim = Claim.objects.select_related("report__location", "claimant", "reviewer").filter(pk=pk).first()
        if not claim or not can_view_claim(request.user, claim):
            return Response({"detail": "Not found."}, status=404)
        return Response(claim_dict(claim, request.user, request))


class ClaimAction(APIView):
    action = None

    def post(self, request, pk):
        try:
            if self.action == "review":
                claim = services.review_claim(request.user, pk, request.data.get("decision"), request.data.get("reason"))
            elif self.action == "withdraw":
                claim = services.withdraw_claim(request.user, pk)
            elif self.action == "dispute":
                claim = services.open_dispute(request.user, pk, request.data.get("note"))
            elif self.action == "confirm_return":
                claim = services.confirm_peer_return(request.user, pk)
            elif self.action == "handover":
                when = parse_datetime(str(request.data.get("scheduled_for") or ""))
                if when is None:
                    raise ClaimError("Provide scheduled_for as an ISO date-time.")
                if timezone.is_naive(when):
                    when = timezone.make_aware(when)
                services.schedule_handover(request.user, pk, when, request.data.get("location"), request.data.get("notes"))
                claim = Claim.objects.get(pk=pk)
        except ClaimError as e:
            return _err(e)
        claim = Claim.objects.select_related("report__location", "claimant", "reviewer").get(pk=claim.pk)
        return Response(claim_dict(claim, request.user, request))


class EvidenceUpload(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        claim = Claim.objects.filter(pk=pk, claimant=request.user).first()
        if not claim:
            return Response({"detail": "Not found."}, status=404)
        if claim.status not in ("pending", "under_review"):
            return Response({"detail": "Evidence can only be added while the claim is open."}, status=409)
        f = request.FILES.get("file")
        if not f:
            return Response({"file": ["Choose a file."]}, status=400)
        if f.size > MAX_EVIDENCE:
            return Response({"file": ["File must be under 5 MB."]}, status=400)
        head = f.read(12)
        f.seek(0)
        is_pdf = head.startswith(b"%PDF")
        if not is_pdf:
            from apps.reports.validators import validate_image_file
            try:
                validate_image_file(f)
            except serializers.ValidationError as e:
                return Response({"file": e.detail}, status=400)
        if claim.evidence.count() >= 5:
            return Response({"file": ["At most 5 evidence files per claim."]}, status=400)
        ev = ClaimEvidence.objects.create(claim=claim, file=f, original_name=f.name[:200],
                                          note=str(request.data.get("note", ""))[:300])
        audit(request.user, "claim.evidence_added", claim)
        return Response({"id": ev.id, "name": ev.original_name}, status=201)


class EvidenceDownload(APIView):
    """Private evidence: only the claimant and people authorised to review the claim."""

    def get(self, request, pk):
        ev = ClaimEvidence.objects.select_related("claim__report").filter(pk=pk).first()
        if not ev or not can_view_claim(request.user, ev.claim):
            return Response({"detail": "Not found."}, status=404)
        audit(request.user, "claim.evidence_downloaded", ev.claim, {"evidence": ev.pk}, request)
        ctype = mimetypes.guess_type(ev.original_name)[0] or "application/octet-stream"
        return FileResponse(ev.file.open("rb"), as_attachment=True, filename=ev.original_name, content_type=ctype)


# ---------------- staff inventory & handovers ----------------

def inventory_dict(inv, detail=False, request=None):
    report = inv.report
    claims = list(report.claims.select_related("claimant")) if report else []
    data = {"id": inv.id, "reference": inv.reference, "name": inv.name, "category": inv.category.name,
            "category_id": inv.category_id, "received_at": inv.received_at, "received_by": inv.received_by.display_name,
            "storage_location": inv.storage_location, "condition_notes": inv.condition_notes, "status": inv.status,
            "status_display": inv.get_status_display(), "report_id": inv.report_id,
            "report_status": report.status if report else None,
            "thumbnail": thumbnail(report, request) if report else None,
            "claim_count": len([c for c in claims if c.status in services.LIVE])}
    if detail:
        data["report_private_details"] = report.private_details if report else ""
        data["report_description"] = report.description if report else ""
        data["claims"] = [{"id": c.id, "status": c.status, "claimant_name": c.claimant.full_name,
                           "created_at": c.created_at} for c in claims]
        data["handovers"] = [handover_dict(h) for h in inv.handovers.select_related("claim__report", "confirmed_by",
                                                                                   "scheduled_by", "inventory")]
    return data


class InventoryListCreate(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        qs = InventoryRecord.objects.select_related("category", "received_by", "report").prefetch_related("report__images")
        p = request.query_params
        if p.get("q"):
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=p["q"]) | Q(reference__icontains=p["q"]) | Q(storage_location__icontains=p["q"]))
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("category"):
            qs = qs.filter(category_id=p["category"])
        pag = StandardPagination()
        page = pag.paginate_queryset(qs, request)
        return pag.get_paginated_response([inventory_dict(i, request=request) for i in page])

    def post(self, request):
        storage = (request.data.get("storage_location") or "").strip()
        if not storage:
            return Response({"storage_location": ["Where is the item stored?"]}, status=400)
        link = request.data.get("report")
        if link:
            report = ItemReport.objects.filter(pk=link, type="found").first()
            if not report:
                return Response({"report": ["Found report not found."]}, status=400)
            if InventoryRecord.objects.filter(report=report).exists():
                return Response({"report": ["This report already has an inventory record."]}, status=409)
            report.held_by_staff = True
            report.save(update_fields=["held_by_staff", "updated_at"])
        else:
            data = request.data.copy()
            data["type"] = "found"
            report = create_report(request.user, data, request.FILES.getlist("images"), held_by_staff=True, request=request)
        inv = InventoryRecord.objects.create(
            report=report, name=report.title, category=report.category, received_at=timezone.now(),
            received_by=request.user, storage_location=storage[:160],
            condition_notes=(request.data.get("condition_notes") or "")[:500])
        audit(request.user, "inventory.created", inv, {"report": report.pk}, request)
        return Response(inventory_dict(inv, True, request), status=201)


class InventoryDetail(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request, pk):
        inv = InventoryRecord.objects.select_related("category", "received_by", "report").filter(pk=pk).first()
        if not inv:
            return Response(status=404)
        return Response(inventory_dict(inv, True, request))

    def patch(self, request, pk):
        inv = InventoryRecord.objects.select_related("category", "received_by", "report").filter(pk=pk).first()
        if not inv:
            return Response(status=404)
        changed = {}
        for f in ("storage_location", "condition_notes"):
            if f in request.data:
                setattr(inv, f, str(request.data[f]).strip()[:500])
                changed[f] = getattr(inv, f)
        if request.data.get("status") == "disposed" and inv.status == "stored":
            if not can_release(request.user):
                return Response({"detail": "Only staff authorised to release items can dispose of items."}, status=403)
            if inv.report and inv.report.claims.filter(status__in=services.LIVE).exists():
                return Response({"detail": "Resolve open claims first."}, status=409)
            inv.status = "disposed"
            changed["status"] = "disposed"
        if not inv.storage_location:
            return Response({"storage_location": ["Required."]}, status=400)
        inv.save()
        audit(request.user, "inventory.updated", inv, changed, request)
        return Response(inventory_dict(inv, True, request))


class HandoverList(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        qs = HandoverRecord.objects.select_related("claim__report", "confirmed_by", "scheduled_by", "inventory")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        pag = StandardPagination()
        page = pag.paginate_queryset(qs, request)
        return pag.get_paginated_response([handover_dict(h) for h in page])


class HandoverAction(APIView):
    permission_classes = [IsStaffRole]
    action = None

    def post(self, request, pk):
        try:
            h = (services.confirm_handover if self.action == "confirm" else services.cancel_handover)(request.user, pk)
        except ClaimError as e:
            return _err(e)
        h = HandoverRecord.objects.select_related("claim__report", "confirmed_by", "scheduled_by", "inventory").get(pk=h.pk)
        return Response(handover_dict(h))
