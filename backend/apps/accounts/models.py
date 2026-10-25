from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        FACULTY = "faculty", "Faculty"
        STAFF = "staff", "Campus staff"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT, db_index=True)
    student_id = models.CharField(max_length=40, blank=True)
    department = models.CharField(max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    campus = models.ForeignKey("core.Campus", null=True, blank=True, on_delete=models.SET_NULL, related_name="users")
    # Verification: a real token flow, or manual verification by an administrator.
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, blank=True, db_index=True)
    # Staff approval: students may request staff access; only an admin can grant it.
    staff_requested = models.BooleanField(default=False)  # any elevated-role request (staff or admin)
    requested_role = models.CharField(max_length=10, blank=True)
    staff_title = models.CharField(max_length=80, blank=True)
    can_review_claims = models.BooleanField(default=False)
    can_release_items = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["role", "is_active"])]

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.email_verified = True
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email.split("@")[0]

    @property
    def display_name(self):
        """Safe public name: first name + last initial only."""
        if self.first_name:
            initial = f" {self.last_name[0]}." if self.last_name else ""
            return f"{self.first_name}{initial}"
        return "Campus member"

    @property
    def is_staff_role(self):
        return self.role in (self.Role.STAFF, self.Role.ADMIN)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN
