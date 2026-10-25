import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


def email_domain_allowed(email):
    """True if the email's domain equals, or is a subdomain of, any configured entry ("*" allows all)."""
    domain = email.rsplit("@", 1)[-1].lower()
    for rule in settings.ALLOWED_COLLEGE_EMAIL_DOMAINS:
        rule = rule.strip().lower().lstrip("@")
        if rule == "*":
            return True
        rule = rule.lstrip(".")
        if rule and (domain == rule or domain.endswith("." + rule)):
            return True
    return False


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    campus_name = serializers.CharField(source="campus.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "display_name", "role",
                  "student_id", "department", "year", "campus", "campus_name", "staff_requested", "requested_role",
                  "staff_title", "can_review_claims", "can_release_items", "email_verified", "date_joined"]
        read_only_fields = ["id", "email", "role", "staff_requested", "requested_role", "staff_title", "can_review_claims",
                            "can_release_items", "email_verified", "date_joined"]


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    student_id = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    department = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    year = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=8, default=None)
    campus = serializers.IntegerField(required=False, allow_null=True, default=None)
    account_type = serializers.ChoiceField(choices=["student", "faculty", "staff", "admin"], required=False, default="student")

    def validate_email(self, value):
        value = value.strip().lower()
        if not email_domain_allowed(value):
            raise serializers.ValidationError(
                "Please use your college or university email address (for example name@college.edu or name@college.ac.in).")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_full_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Enter your full name.")
        return value

    def validate(self, attrs):
        validate_password(attrs["password"], user=User(email=attrs["email"], first_name=attrs["full_name"]))
        return attrs

    def create(self, validated):
        from apps.core.models import Campus
        parts = validated["full_name"].split(" ", 1)
        campus = Campus.objects.filter(pk=validated.get("campus")).first() if validated.get("campus") else None
        kind = validated["account_type"]
        # The client only REQUESTS a type. Student/faculty are ordinary accounts; staff and admin start as
        # ordinary faculty-level accounts until an existing administrator approves them.
        role = kind if kind in ("student", "faculty") else User.Role.STUDENT
        user = User(username=validated["email"], email=validated["email"], first_name=parts[0],
                    last_name=parts[1] if len(parts) > 1 else "", student_id=validated["student_id"],
                    department=validated["department"], year=validated["year"], campus=campus,
                    staff_requested=kind in ("staff", "admin"), requested_role=kind if kind in ("staff", "admin") else "", role=role,
                    email_verified=False, verification_token=secrets.token_urlsafe(32))
        user.set_password(validated["password"])
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Current password is incorrect."})
        validate_password(attrs["new_password"], user=user)
        return attrs
