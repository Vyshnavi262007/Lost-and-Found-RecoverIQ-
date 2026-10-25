from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("admin/categories", views.CategoryViewSet, basename="admin-category")
router.register("admin/locations", views.LocationViewSet, basename="admin-location")

urlpatterns = [
    path("dashboard/student/", views.StudentDashboard.as_view()),
    path("dashboard/staff/", views.StaffDashboard.as_view()),
    path("admin/analytics/", views.Analytics.as_view()),
    path("admin/users/", views.UserList.as_view()),
    path("admin/users/<int:pk>/", views.UserDetail.as_view()),
    path("admin/staff-requests/", views.StaffRequests.as_view()),
    path("admin/staff-requests/<int:pk>/", views.StaffRequests.as_view()),
    path("admin/reports/", views.ModerationReports.as_view()),
    path("admin/reports/<int:pk>/moderate/", views.ModerationReports.as_view()),
    path("admin/abuse/", views.AbuseList.as_view()),
    path("admin/abuse/<int:pk>/", views.AbuseList.as_view()),
    path("admin/duplicates/", views.Duplicates.as_view()),
    path("admin/disputes/", views.Disputes.as_view()),
    path("admin/disputes/<int:pk>/", views.Disputes.as_view()),
    path("admin/audit-logs/", views.AuditLogList.as_view()),
    path("admin/settings/", views.SettingsView.as_view()),
    path("", include(router.urls)),
]
