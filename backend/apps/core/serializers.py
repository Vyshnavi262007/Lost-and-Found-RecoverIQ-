from rest_framework import serializers

from .models import AuditLog, CampusLocation, ItemCategory, Notification


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ["id", "name", "slug", "group", "is_active"]


class LocationSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source="campus.name", read_only=True)

    class Meta:
        model = CampusLocation
        fields = ["id", "campus", "campus_name", "name", "block", "x_m", "y_m", "is_active"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "is_read", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "actor_name", "action", "target_type", "target_id", "detail", "created_at"]

    def get_actor_name(self, obj):
        return obj.actor.email if obj.actor else "system"
