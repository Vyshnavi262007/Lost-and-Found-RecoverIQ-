from .models import AuditLog, Notification
from .site_settings import get_setting

_NOTIFY_FLAGS = {"match": "notify_on_match", "comment": "notify_on_comment", "message": "notify_on_message"}


def audit(actor, action, target=None, detail=None, request=None):
    ip = request.META.get("REMOTE_ADDR") if request is not None else None
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None, action=action,
        target_type=type(target).__name__ if target is not None else "",
        target_id=str(target.pk) if target is not None else "", detail=detail or {}, ip_address=ip)


def notify(user, kind, title, body="", link=""):
    """Persist an in-app notification. (No email is sent from here.)"""
    if user is None or not user.is_active:
        return None
    flag = _NOTIFY_FLAGS.get(kind)
    if flag and not get_setting(flag):
        return None
    return Notification.objects.create(user=user, kind=kind, title=title[:200], body=body[:400], link=link[:200])
