from django.conf import settings
from django.db import models


class Campus(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.SlugField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "campuses"

    def __str__(self):
        return self.name


class CampusLocation(models.Model):
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name="locations")
    name = models.CharField(max_length=120)
    block = models.CharField(max_length=60, blank=True)
    # Local campus-grid coordinates in metres, used to estimate walking proximity.
    x_m = models.FloatField(null=True, blank=True)
    y_m = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["campus", "name"], name="uniq_location_per_campus")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class ItemCategory(models.Model):
    GROUPS = [("documents", "Documents & cards"), ("electronics", "Electronics"), ("personal", "Personal items"),
              ("study", "Study materials"), ("other", "Other")]
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    group = models.CharField(max_length=20, choices=GROUPS, default="other")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "item categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SiteSetting(models.Model):
    key = models.CharField(max_length=60, unique=True)
    value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="audit_events")
    action = models.CharField(max_length=80, db_index=True)
    target_type = models.CharField(max_length=60, blank=True)
    target_id = models.CharField(max_length=40, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Notification(models.Model):
    class Kind(models.TextChoices):
        MATCH = "match", "Possible match"
        COMMENT = "comment", "Comment"
        MESSAGE = "message", "Message"
        CLAIM = "claim", "Claim"
        HANDOVER = "handover", "Handover"
        STATUS = "status", "Report status"
        SYSTEM = "system", "System"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=400, blank=True)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "is_read"])]
