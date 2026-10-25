from django.urls import path

from . import views

urlpatterns = [
    path("claims/questions/", views.ClaimQuestions.as_view()),
    path("claims/", views.ClaimListCreate.as_view()),
    path("claims/<int:pk>/", views.ClaimDetail.as_view()),
    path("claims/<int:pk>/review/", views.ClaimAction.as_view(action="review")),
    path("claims/<int:pk>/withdraw/", views.ClaimAction.as_view(action="withdraw")),
    path("claims/<int:pk>/dispute/", views.ClaimAction.as_view(action="dispute")),
    path("claims/<int:pk>/confirm-return/", views.ClaimAction.as_view(action="confirm_return")),
    path("claims/<int:pk>/handover/", views.ClaimAction.as_view(action="handover")),
    path("claims/<int:pk>/evidence/", views.EvidenceUpload.as_view()),
    path("claim-evidence/<int:pk>/download/", views.EvidenceDownload.as_view()),
    path("inventory/", views.InventoryListCreate.as_view()),
    path("inventory/<int:pk>/", views.InventoryDetail.as_view()),
    path("handovers/", views.HandoverList.as_view()),
    path("handovers/<int:pk>/confirm/", views.HandoverAction.as_view(action="confirm")),
    path("handovers/<int:pk>/cancel/", views.HandoverAction.as_view(action="cancel")),
]
