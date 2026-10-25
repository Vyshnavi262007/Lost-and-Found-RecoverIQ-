from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.services import audit, notify
from apps.core.site_settings import get_setting

from .matching_service import MATCH_FIELDS, recompute_matches
from .models import AbuseReport, Bookmark, Comment, ItemImage, ItemReport, Match
from .queries import annotated, apply_filters, visible_reports
from .serializers import (AbuseSerializer, CommentSerializer, MatchSerializer, ReportDetailSerializer,
                          ReportListSerializer, ReportWriteSerializer)
from .validators import validate_images


def create_report(user, data, files, held_by_staff=False, request=None):
    """Shared by the report form and the staff inventory form."""
    ser = ReportWriteSerializer(data=data)
    ser.is_valid(raise_exception=True)
    try:
        validate_images(files)
    except serializers.ValidationError as e:
        raise serializers.ValidationError({"images": e.detail})
    moderation = "approved"
    if user.role in ("student", "faculty") and get_setting("require_report_approval"):
        moderation = "pending"
    with transaction.atomic():
        report = ser.save(reporter=user, moderation=moderation, held_by_staff=held_by_staff)
        for i, f in enumerate(files):
            ItemImage.objects.create(report=report, image=f, order=i)
    audit(user, "report.created", report, {"type": report.type}, request)
    recompute_matches(report)
    return report


class ReportListCreate(APIView):
    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "write"
            return [ScopedRateThrottle()]
        return []

    def get(self, request):
        qs = annotated(ItemReport.objects.filter(moderation="approved"), request.user)
        qs = apply_filters(qs, request.query_params)
        if request.query_params.get("mine") == "1":
            qs = qs.filter(reporter=request.user)
        from rest_framework.pagination import PageNumberPagination
        from apps.core.pagination import StandardPagination
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ReportListSerializer(page, many=True, context={"request": request}).data)

    def post(self, request):
        report = create_report(request.user, request.data, request.FILES.getlist("images"), request=request)
        report = annotated(ItemReport.objects.filter(pk=report.pk), request.user).get()
        return Response(ReportDetailSerializer(report, context={"request": request}).data, status=201)


class MyReports(ListAPIView):
    serializer_class = ReportListSerializer

    def get_queryset(self):
        qs = annotated(ItemReport.objects.filter(reporter=self.request.user), self.request.user)
        return apply_filters(qs, self.request.query_params)


class ReportDetail(APIView):
    def _get(self, request, pk):
        return annotated(visible_reports(request.user).filter(pk=pk), request.user).first()

    def get(self, request, pk):
        report = self._get(request, pk)
        if not report:
            return Response({"detail": "Not found."}, status=404)
        return Response(ReportDetailSerializer(report, context={"request": request}).data)

    def patch(self, request, pk):
        report = self._get(request, pk)
        if not report:
            return Response({"detail": "Not found."}, status=404)
        if report.reporter_id != request.user.id and request.user.role != "admin":
            return Response({"detail": "You can only edit your own reports."}, status=403)
        if report.status != "open":
            return Response({"detail": "Only open reports can be edited."}, status=409)
        ser = ReportWriteSerializer(report, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        new_files = request.FILES.getlist("images")
        remove_ids = [int(i) for i in request.data.getlist("remove_image_ids")] if hasattr(request.data, "getlist") else []
        remaining = report.images.exclude(id__in=remove_ids).count()
        try:
            validate_images(new_files, existing=remaining)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"images": e.detail})
        with transaction.atomic():
            ser.save()
            report.images.filter(id__in=remove_ids).delete()
            start = report.images.count()
            for i, f in enumerate(new_files):
                ItemImage.objects.create(report=report, image=f, order=start + i)
        audit(request.user, "report.updated", report, request=request)
        if MATCH_FIELDS & set(ser.validated_data) or new_files or remove_ids:
            recompute_matches(report)
        report = self._get(request, pk)
        return Response(ReportDetailSerializer(report, context={"request": request}).data)


class ReportClose(APIView):
    def post(self, request, pk):
        report = ItemReport.objects.filter(pk=pk).first()
        if not report:
            return Response({"detail": "Not found."}, status=404)
        if report.reporter_id != request.user.id and request.user.role != "admin":
            return Response({"detail": "You can only close your own reports."}, status=403)
        if report.status != "open":
            return Response({"detail": "Only open reports can be closed (an approved claim must be completed or withdrawn first)."},
                            status=409)
        report.status = "closed"
        report.save(update_fields=["status", "updated_at"])
        report.lost_matches.all().delete()
        report.found_matches.all().delete()
        audit(request.user, "report.closed", report, request=request)
        return Response({"status": "closed"})


class PublicRecent(APIView):
    """Landing page: safe public cards only. No private details, no user identifiers."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        qs = annotated(ItemReport.objects.filter(moderation="approved", status="open"), request.user)
        qs = apply_filters(qs, request.query_params)[:12]
        data = ReportListSerializer(qs, many=True, context={"request": request}).data
        for d in data:
            d.pop("is_owner", None)
        return Response(data)


class ReportMatches(APIView):
    def get(self, request, pk):
        report = ItemReport.objects.filter(pk=pk).first()
        if not report:
            return Response({"detail": "Not found."}, status=404)
        if report.reporter_id != request.user.id and request.user.role not in ("staff", "admin"):
            return Response({"detail": "Only the report owner can view its matches."}, status=403)
        side = "lost_report" if report.type == "lost" else "found_report"
        qs = Match.objects.filter(**{side: report}, status="new").exclude(
            lost_report__moderation="removed").exclude(found_report__moderation="removed")
        qs = qs.select_related("lost_report__category", "lost_report__location", "lost_report__reporter",
                               "found_report__category", "found_report__location", "found_report__reporter")
        return Response(MatchSerializer(qs, many=True, context={"request": request}).data)


class MyMatches(ListAPIView):
    serializer_class = MatchSerializer

    def get_queryset(self):
        u = self.request.user
        return Match.objects.filter(Q(lost_report__reporter=u) | Q(found_report__reporter=u), status="new").exclude(
            lost_report__moderation="removed").exclude(found_report__moderation="removed").select_related(
            "lost_report__category", "lost_report__location", "lost_report__reporter",
            "found_report__category", "found_report__location", "found_report__reporter")


class MatchDismiss(APIView):
    def post(self, request, pk):
        m = Match.objects.filter(Q(lost_report__reporter=request.user) | Q(found_report__reporter=request.user),
                                 pk=pk).first()
        if not m:
            return Response({"detail": "Not found."}, status=404)
        m.status = "dismissed"
        m.save(update_fields=["status", "updated_at"])
        return Response({"status": "dismissed"})


class CommentListCreate(APIView):
    def get(self, request, pk):
        report = visible_reports(request.user).filter(pk=pk).first()
        if not report:
            return Response({"detail": "Not found."}, status=404)
        qs = report.comments.filter(is_removed=False).select_related("author")
        return Response(CommentSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request, pk):
        report = visible_reports(request.user).filter(pk=pk).first()
        if not report:
            return Response({"detail": "Not found."}, status=404)
        body = (request.data.get("body") or "").strip()
        if not body or len(body) > 1000:
            return Response({"body": ["Comment must be 1-1000 characters."]}, status=400)
        c = Comment.objects.create(report=report, author=request.user, body=body)
        if report.reporter_id != request.user.id:
            notify(report.reporter, "comment", f"New comment on \"{report.title}\"",
                   f"{request.user.display_name}: {body[:120]}", f"/reports/{report.pk}")
        return Response(CommentSerializer(c, context={"request": request}).data, status=201)


class CommentDetail(APIView):
    def _get(self, request, pk):
        return Comment.objects.filter(pk=pk, is_removed=False).select_related("author", "report").first()

    def patch(self, request, pk):
        c = self._get(request, pk)
        if not c:
            return Response(status=404)
        if c.author_id != request.user.id:
            return Response({"detail": "You can only edit your own comments."}, status=403)
        body = (request.data.get("body") or "").strip()
        if not body or len(body) > 1000:
            return Response({"body": ["Comment must be 1-1000 characters."]}, status=400)
        c.body = body
        c.save(update_fields=["body", "updated_at"])
        return Response(CommentSerializer(c, context={"request": request}).data)

    def delete(self, request, pk):
        c = self._get(request, pk)
        if not c:
            return Response(status=404)
        if c.author_id != request.user.id and request.user.role != "admin":
            return Response({"detail": "Not allowed."}, status=403)
        c.is_removed = True
        c.save(update_fields=["is_removed", "updated_at"])
        if c.author_id != request.user.id:
            audit(request.user, "comment.removed", c, request=request)
        return Response(status=204)


class BookmarkToggle(APIView):
    def post(self, request, pk):
        report = visible_reports(request.user).filter(pk=pk).first()
        if not report:
            return Response(status=404)
        Bookmark.objects.get_or_create(user=request.user, report=report)
        return Response({"bookmarked": True}, status=201)

    def delete(self, request, pk):
        Bookmark.objects.filter(user=request.user, report_id=pk).delete()
        return Response({"bookmarked": False})


class BookmarkList(ListAPIView):
    serializer_class = ReportListSerializer

    def get_queryset(self):
        ids = Bookmark.objects.filter(user=self.request.user).values_list("report_id", flat=True)
        return annotated(visible_reports(self.request.user).filter(pk__in=ids), self.request.user).order_by("-created_at")


class ReportAbuse(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "abuse"

    def post(self, request, pk):
        report = visible_reports(request.user).filter(pk=pk).first()
        if not report:
            return Response(status=404)
        ser = AbuseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        comment = None
        if request.data.get("comment_id"):
            comment = report.comments.filter(pk=request.data["comment_id"]).first()
        AbuseReport.objects.create(reporter=request.user, report=None if comment else report, comment=comment,
                                   **ser.validated_data)
        return Response({"detail": "Thank you. A moderator will review this."}, status=201)
