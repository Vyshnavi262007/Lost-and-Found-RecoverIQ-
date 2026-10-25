from django.urls import path

from . import views

urlpatterns = [
    path("conversations/", views.ConversationList.as_view()),
    path("conversations/<int:pk>/", views.ConversationDetail.as_view()),
    path("conversations/<int:pk>/messages/", views.MessageCreate.as_view()),
]
