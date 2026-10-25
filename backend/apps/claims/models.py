import os
import secrets
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Q


def get_private_storage():
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def evidence_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".pdf"):
        ext = ".bin"
    return f"claim_evidence/{uuid.uuid4().hex}{ext}"


class Claim(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        COMPLETED = "completed", "Completed"

    report = models.ForeignKey("reports.ItemReport", on_delete=models.PROTECT, related_name="claims")
    claimant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="claims")
    description = models.TextField(max_length=2000)
    answers = models.JSONField(default=list)  # [{"question": ..., "answer": ...}]
    preferred_handover = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="reviewed_claims")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.CharField(max_length=500, blank=True)
    dispute_status = models.CharField(max_length=10, default="none",
                                      choices=[("none", "None"), ("open", "Open"), ("upheld", "Rejection upheld"),
                                               ("reopened", "Reopened")])
    dispute_note = models.CharField(max_length=500, blank=True)
    dispute_resolution = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # one live claim per person per item
            models.UniqueConstraint(fields=["report", "claimant"], name="one_live_claim_per_claimant",
                                    condition=Q(status__in=["pending", "under_review", "approved"])),
            # never two approved/completed claims on the same found item
            models.UniqueConstraint(fields=["report"], name="one_winning_claim_per_report",
                                    condition=Q(status__in=["approved", "completed"])),
            models.CheckConstraint(
                condition=~Q(status__in=["approved", "rejected", "completed"]) | Q(reviewer__isnull=False),
                name="decided_claim_has_reviewer"),
        ]


class ClaimEvent(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=14)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class ClaimEvidence(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="evidence")
    file = models.FileField(upload_to=evidence_path, storage=get_private_storage)
    original_name = models.CharField(max_length=200)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


def new_inventory_reference():
    from django.utils import timezone
    while True:
        ref = f"INV-{timezone.now().year}-{secrets.token_hex(3).upper()}"
        if not InventoryRecord.objects.filter(reference=ref).exists():
            return ref


class InventoryRecord(models.Model):
    class Status(models.TextChoices):
        STORED = "stored", "In storage"
        RETURNED = "returned", "Returned to owner"
        DISPOSED = "disposed", "Disposed / transferred"

    reference = models.CharField(max_length=24, unique=True, default=new_inventory_reference)
    report = models.OneToOneField("reports.ItemReport", null=True, blank=True, on_delete=models.PROTECT,
                                  related_name="inventory")
    name = models.CharField(max_length=160)
    category = models.ForeignKey("core.ItemCategory", on_delete=models.PROTECT, related_name="inventory")
    received_at = models.DateTimeField()
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="received_items")
    storage_location = models.CharField(max_length=160)
    condition_notes = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.STORED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_at", "-id"]


class HandoverRecord(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=20, unique=True)
    inventory = models.ForeignKey(InventoryRecord, null=True, blank=True, on_delete=models.PROTECT,
                                  related_name="handovers")
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="handovers")
    scheduled_for = models.DateTimeField()
    location = models.CharField(max_length=160)
    notes = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    scheduled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="confirmed_handovers")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_for"]
        constraints = [
            models.UniqueConstraint(fields=["claim"], condition=Q(status="scheduled"),
                                    name="one_scheduled_handover_per_claim"),
            models.CheckConstraint(
                condition=~Q(status="completed") | (Q(confirmed_by__isnull=False) & Q(confirmed_at__isnull=False)),
                name="completed_handover_is_confirmed"),
        ]
