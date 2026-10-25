from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Conversation(models.Model):
    report = models.ForeignKey("reports.ItemReport", on_delete=models.CASCADE, related_name="conversations")
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="started_conversations")
    other = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["report", "initiator"], name="uniq_conversation_per_report_initiator"),
            models.CheckConstraint(condition=~Q(initiator=F("other")), name="conversation_two_people"),
        ]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.CharField(max_length=2000)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "read_at"])]
