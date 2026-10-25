import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


def report_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    return f"reports/{uuid.uuid4().hex[:2]}/{uuid.uuid4().hex}{ext}"  # random names, no user input in path


class ItemReport(models.Model):
    class Type(models.TextChoices):
        LOST = "lost", "Lost"
        FOUND = "found", "Found"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLAIM_PENDING = "claim_pending", "Claim approved - awaiting return"
        RETURNED = "returned", "Returned"
        CLOSED = "closed", "Closed"
        EXPIRED = "expired", "Expired"

    class Moderation(models.TextChoices):
        APPROVED = "approved", "Approved"
        PENDING = "pending", "Pending review"
        REMOVED = "removed", "Removed"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reports")
    type = models.CharField(max_length=5, choices=Type.choices)
    title = models.CharField(max_length=160)
    category = models.ForeignKey("core.ItemCategory", on_delete=models.PROTECT, related_name="reports")
    description = models.TextField(max_length=3000)
    brand = models.CharField(max_length=80, blank=True)
    color = models.CharField(max_length=60, blank=True)
    features = models.TextField(max_length=1000, blank=True)
    location = models.ForeignKey("core.CampusLocation", on_delete=models.PROTECT, related_name="reports")
    building = models.CharField(max_length=80, blank=True)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    # PRIVATE: only the owner, staff and admins ever receive this. Used to verify claims.
    private_details = models.TextField(max_length=2000, blank=True)
    contact_preference = models.CharField(max_length=10, default="in_app",
                                          choices=[("in_app", "In-app messages"), ("staff_desk", "Via campus desk")])
    notes = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.OPEN, db_index=True)
    moderation = models.CharField(max_length=10, choices=Moderation.choices, default=Moderation.APPROVED,
                                  db_index=True)
    held_by_staff = models.BooleanField(default=False)
    returned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["type", "status", "moderation"]), models.Index(fields=["date"])]
        constraints = [
            models.CheckConstraint(condition=~Q(status="returned") | Q(returned_at__isnull=False),
                                   name="returned_has_timestamp"),
        ]

    def __str__(self):
        return f"[{self.type}] {self.title}"


class ItemImage(models.Model):
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=report_image_path)
    order = models.PositiveSmallIntegerField(default=0)
    embedding = models.JSONField(null=True, blank=True)  # cache for optional visual similarity
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]


class Match(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        DISMISSED = "dismissed", "Dismissed"

    lost_report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name="lost_matches")
    found_report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name="found_matches")
    score = models.FloatField()
    components = models.JSONField(default=dict)
    explanation = models.CharField(max_length=400, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score", "-id"]
        indexes = [models.Index(fields=["status", "-score"])]
        constraints = [
            models.UniqueConstraint(fields=["lost_report", "found_report"], name="uniq_match_pair"),
            models.CheckConstraint(condition=~Q(lost_report=F("found_report")), name="match_not_self"),
        ]


class Comment(models.Model):
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="comments")
    body = models.CharField(max_length=1000)
    is_removed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    report = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "report"], name="uniq_bookmark")]


class AbuseReport(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="abuse_reports")
    report = models.ForeignKey(ItemReport, null=True, blank=True, on_delete=models.CASCADE, related_name="abuse_reports")
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE, related_name="abuse_reports")
    reason = models.CharField(max_length=20, choices=[("spam", "Spam"), ("fake", "Fake or misleading"),
                                                      ("inappropriate", "Inappropriate"), ("private", "Shares private info"),
                                                      ("other", "Other")])
    details = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    resolution_note = models.CharField(max_length=500, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(
            condition=Q(report__isnull=False) | Q(comment__isnull=False), name="abuse_has_target")]
