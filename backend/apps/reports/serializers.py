from datetime import date as date_cls

from rest_framework import serializers

from apps.core.models import CampusLocation, ItemCategory

from .models import AbuseReport, Comment, ItemReport, Match


def _abs(request, url):
    return request.build_absolute_uri(url) if request else url


def thumbnail(report, request):
    imgs = list(report.images.all())
    return _abs(request, imgs[0].image.url) if imgs else None


def can_see_private(user, report):
    return user.is_authenticated and (user.id == report.reporter_id or user.role in ("staff", "admin"))


class ReportListSerializer(serializers.ModelSerializer):
    """Public-safe card: no private details, no contact info, no student identifiers."""
    category = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    reporter_name = serializers.CharField(source="reporter.display_name", read_only=True)
    thumbnail = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(read_only=True, default=0)
    is_bookmarked = serializers.BooleanField(read_only=True, default=False)
    is_owner = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()

    class Meta:
        model = ItemReport
        fields = ["id", "type", "title", "category", "short_description", "location", "building", "date",
                  "status", "moderation", "held_by_staff", "created_at", "reporter_name", "thumbnail",
                  "comment_count", "is_bookmarked", "is_owner"]

    def get_category(self, o):
        return {"id": o.category_id, "name": o.category.name}

    def get_location(self, o):
        return {"id": o.location_id, "name": o.location.name}

    def get_thumbnail(self, o):
        return thumbnail(o, self.context.get("request"))

    def get_is_owner(self, o):
        r = self.context.get("request")
        return bool(r and r.user.is_authenticated and r.user.id == o.reporter_id)

    def get_short_description(self, o):
        return o.description if len(o.description) <= 180 else o.description[:177] + "..."


class ReportDetailSerializer(ReportListSerializer):
    images = serializers.SerializerMethodField()
    private_details = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    has_active_claim = serializers.SerializerMethodField()

    class Meta(ReportListSerializer.Meta):
        fields = ReportListSerializer.Meta.fields + [
            "description", "brand", "color", "features", "time", "notes", "contact_preference",
            "images", "private_details", "can_edit", "has_active_claim"]

    def get_images(self, o):
        r = self.context.get("request")
        return [{"id": i.id, "url": _abs(r, i.image.url)} for i in o.images.all()]

    def get_private_details(self, o):
        r = self.context.get("request")
        return o.private_details if r and can_see_private(r.user, o) else None

    def get_can_edit(self, o):
        r = self.context.get("request")
        return bool(r and r.user.is_authenticated and (r.user.id == o.reporter_id or r.user.role == "admin")
                    and o.status == "open")

    def get_has_active_claim(self, o):
        r = self.context.get("request")
        if not r or not r.user.is_authenticated or o.type != "found":
            return False
        return o.claims.filter(claimant=r.user, status__in=["pending", "under_review", "approved"]).exists()


class ReportWriteSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ItemCategory.objects.filter(is_active=True))
    location = serializers.PrimaryKeyRelatedField(queryset=CampusLocation.objects.filter(is_active=True))
    time = serializers.TimeField(required=False, allow_null=True)

    class Meta:
        model = ItemReport
        fields = ["type", "title", "category", "description", "brand", "color", "features", "location",
                  "building", "date", "time", "private_details", "contact_preference", "notes"]
        extra_kwargs = {"brand": {"required": False}, "color": {"required": False},
                        "features": {"required": False}, "building": {"required": False},
                        "private_details": {"required": False}, "notes": {"required": False},
                        "contact_preference": {"required": False}}

    def validate_title(self, v):
        v = v.strip()
        if len(v) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters.")
        return v

    def validate_description(self, v):
        v = v.strip()
        if len(v) < 10:
            raise serializers.ValidationError("Please describe the item in at least 10 characters.")
        return v

    def validate_date(self, v):
        if v > date_cls.today():
            raise serializers.ValidationError("Date cannot be in the future.")
        return v

    def validate_type(self, v):
        if self.instance and v != self.instance.type:
            raise serializers.ValidationError("Report type cannot be changed.")
        return v


class MatchSerializer(serializers.ModelSerializer):
    lost_report = serializers.SerializerMethodField()
    found_report = serializers.SerializerMethodField()
    similarity_estimate = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = ["id", "score", "similarity_estimate", "components", "explanation", "status",
                  "lost_report", "found_report", "created_at"]

    def get_similarity_estimate(self, o):
        return int(round(o.score * 100))

    def get_lost_report(self, o):
        return ReportListSerializer(o.lost_report, context=self.context).data

    def get_found_report(self, o):
        return ReportListSerializer(o.found_report, context=self.context).data


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)
    is_mine = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "body", "author_name", "is_mine", "can_delete", "created_at", "updated_at"]

    def get_is_mine(self, o):
        r = self.context.get("request")
        return bool(r and r.user.id == o.author_id)

    def get_can_delete(self, o):
        r = self.context.get("request")
        return bool(r and (r.user.id == o.author_id or r.user.role == "admin"))


class AbuseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbuseReport
        fields = ["reason", "details"]
