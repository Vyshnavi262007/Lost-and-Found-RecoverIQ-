from django.urls import path

from . import views

urlpatterns = [
    path("public/recent/", views.PublicRecent.as_view()),
    path("reports/", views.ReportListCreate.as_view()),
    path("reports/mine/", views.MyReports.as_view()),
    path("reports/<int:pk>/", views.ReportDetail.as_view()),
    path("reports/<int:pk>/close/", views.ReportClose.as_view()),
    path("reports/<int:pk>/matches/", views.ReportMatches.as_view()),
    path("reports/<int:pk>/comments/", views.CommentListCreate.as_view()),
    path("reports/<int:pk>/bookmark/", views.BookmarkToggle.as_view()),
    path("reports/<int:pk>/abuse/", views.ReportAbuse.as_view()),
    path("comments/<int:pk>/", views.CommentDetail.as_view()),
    path("bookmarks/", views.BookmarkList.as_view()),
    path("matches/", views.MyMatches.as_view()),
    path("matches/<int:pk>/dismiss/", views.MatchDismiss.as_view()),
]
