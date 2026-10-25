from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryList.as_view()),
    path("locations/", views.LocationList.as_view()),
    path("campuses/", views.CampusList.as_view()),
    path("notifications/", views.NotificationList.as_view()),
    path("notifications/summary/", views.NotificationSummary.as_view()),
    path("notifications/read-all/", views.NotificationReadAll.as_view()),
    path("notifications/<int:pk>/read/", views.NotificationRead.as_view()),
]
