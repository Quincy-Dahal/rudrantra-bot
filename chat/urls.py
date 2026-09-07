"""
chat/urls.py

Registers ConversationViewSet with a DRF router. This auto-generates:

    GET  /api/conversations/               - list conversations
    GET  /api/conversations/<id>/          - retrieve one conversation + its messages
    POST /api/conversations/send-message/  - send a message to the bot
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConversationViewSet, MessageFeedbackView

router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
 
urlpatterns = router.urls + [
    path(
        "messages/<int:message_id>/feedback/",
        MessageFeedbackView.as_view(),
        name="message-feedback",
    ),
]