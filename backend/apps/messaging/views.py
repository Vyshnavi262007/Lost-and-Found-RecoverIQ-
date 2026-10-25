from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.services import audit, notify
from apps.reports.queries import visible_reports

from .models import Conversation, Message


def _msg(m, me):
    return {"id": m.id, "body": m.body, "mine": m.sender_id == me.id, "sender_name": m.sender.display_name,
            "created_at": m.created_at, "read": m.read_at is not None}


def _summary(c, me):
    other = c.other if c.initiator_id == me.id else c.initiator
    last = c.messages.order_by("-created_at", "-id").first()
    unread = c.messages.filter(read_at__isnull=True).exclude(sender=me).count()
    return {"id": c.id, "report": {"id": c.report_id, "title": c.report.title, "type": c.report.type},
            "other_name": other.display_name, "last_message": last.body[:100] if last else "",
            "last_at": last.created_at if last else c.created_at, "unread_count": unread}


def _can_access(user, c):
    return user.id in (c.initiator_id, c.other_id)


class ConversationList(APIView):
    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "write"
            return [ScopedRateThrottle()]
        return []

    def get(self, request):
        qs = Conversation.objects.filter(Q(initiator=request.user) | Q(other=request.user)).select_related(
            "report", "initiator", "other")
        return Response([_summary(c, request.user) for c in qs])

    def post(self, request):
        report = visible_reports(request.user).filter(pk=request.data.get("report")).first()
        body = (request.data.get("body") or "").strip()
        if not report:
            return Response({"detail": "Report not found."}, status=404)
        if report.reporter_id == request.user.id:
            return Response({"detail": "You cannot message yourself about your own report."}, status=400)
        if not body or len(body) > 2000:
            return Response({"body": ["Message must be 1-2000 characters."]}, status=400)
        with transaction.atomic():
            conv, _ = Conversation.objects.get_or_create(report=report, initiator=request.user,
                                                        defaults={"other": report.reporter})
            Message.objects.create(conversation=conv, sender=request.user, body=body)
            conv.save()
        notify(report.reporter, "message", f"New message about \"{report.title}\"",
               f"{request.user.display_name}: {body[:120]}", f"/messages/{conv.id}")
        return Response({"id": conv.id}, status=201)


class ConversationDetail(APIView):
    def get(self, request, pk):
        c = Conversation.objects.filter(pk=pk).select_related("report", "initiator", "other").first()
        if not c:
            return Response(status=404)
        if _can_access(request.user, c):
            c.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=timezone.now())
        elif request.user.role == "admin":  # moderator access is always audit-logged
            audit(request.user, "conversation.moderator_view", c, request=request)
        else:
            return Response({"detail": "Not found."}, status=404)
        msgs = c.messages.select_related("sender")
        return Response({**_summary(c, request.user), "messages": [_msg(m, request.user) for m in msgs],
                         "can_reply": _can_access(request.user, c)})


class MessageCreate(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "write"

    def post(self, request, pk):
        c = Conversation.objects.filter(pk=pk).select_related("report", "initiator", "other").first()
        if not c or not _can_access(request.user, c):
            return Response({"detail": "Not found."}, status=404)
        body = (request.data.get("body") or "").strip()
        if not body or len(body) > 2000:
            return Response({"body": ["Message must be 1-2000 characters."]}, status=400)
        m = Message.objects.create(conversation=c, sender=request.user, body=body)
        c.save()
        recipient = c.other if c.initiator_id == request.user.id else c.initiator
        notify(recipient, "message", f"New message about \"{c.report.title}\"",
               f"{request.user.display_name}: {body[:120]}", f"/messages/{c.id}")
        return Response(_msg(m, request.user), status=201)
