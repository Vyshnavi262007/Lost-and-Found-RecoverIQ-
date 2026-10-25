from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CampusLocation, ItemCategory, Campus, Notification
from .serializers import CategorySerializer, LocationSerializer, NotificationSerializer


class CategoryList(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = ItemCategory.objects.filter(is_active=True)


class LocationList(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = LocationSerializer
    pagination_class = None
    queryset = CampusLocation.objects.filter(is_active=True).select_related("campus")


class CampusList(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(list(Campus.objects.filter(is_active=True).values("id", "name", "code")))


class NotificationList(ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") == "1":
            qs = qs.filter(is_read=False)
        return qs


class NotificationSummary(APIView):
    def get(self, request):
        return Response({"unread_count": Notification.objects.filter(user=request.user, is_read=False).count()})


class NotificationRead(APIView):
    def post(self, request, pk):
        n = Notification.objects.filter(user=request.user, pk=pk).first()
        if not n:
            return Response(status=404)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response(NotificationSerializer(n).data)


class NotificationReadAll(APIView):
    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"updated": updated})
