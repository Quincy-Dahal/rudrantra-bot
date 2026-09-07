"""
chat/views.py

The actual chat endpoint. The send_message action:
    1. Looks up an existing Conversation, or starts a new one
    2. Saves the visitor's message
    3. Sends the full conversation history to core.llm.chat()
    4. Saves the bot's reply
    5. Returns the reply plus the conversation_id to continue with

"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.llm import LLMError
from core.llm import chat as llm_chat

from .models import Conversation, Message
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ConversationSerializer,
    MessageFeedbackSerializer,
    MessageSerializer,
)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to conversations and their message history.
    """

    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer

    @extend_schema(
        request=ChatRequestSerializer,
        responses={200: ChatResponseSerializer},
        description=(
            "Send a message to the chatbot. Omit conversation_id to start "
            "a new conversation; include it to continue an existing one."
        ),
    )
    @action(detail=False, methods=["post"], url_path="send-message")
    def send_message(self, request):
        req = ChatRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)

        conversation_id = req.validated_data.get("conversation_id")
        if conversation_id:
            conversation = get_object_or_404(Conversation, id=conversation_id)
        else:
            conversation = Conversation.objects.create()

        user_text = req.validated_data["message"]
        Message.objects.create(
            conversation=conversation, role=Message.Role.USER, content=user_text
        )

        history = [
            {"role": m.role, "content": m.content}
            for m in conversation.messages.all()
        ]

        try:
            reply_text = llm_chat(history)
        except LLMError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        assistant_message = Message.objects.create(
            conversation=conversation, role=Message.Role.ASSISTANT, content=reply_text
        )
        conversation.save()  # bumps updated_at

        response = ChatResponseSerializer(
            {
                "conversation_id": conversation.id,
                "message_id": assistant_message.id,
                "reply": reply_text,
            }
        )
        return Response(response.data, status=status.HTTP_200_OK)


class MessageFeedbackView(APIView):
    """
    PATCH /api/messages/<id>/feedback/

    Lets a customer rate a specific bot reply. Body: {"feedback": "up"},
    {"feedback": "down"}, or {"feedback": null} to clear it. Only works on
    assistant messages - rating your own message doesn't make sense, so a
    user-role message id returns 404 rather than silently accepting it.
    """

    @extend_schema(
        request=MessageFeedbackSerializer,
        responses={200: MessageSerializer},
        description="Set or clear thumbs up/down feedback on a specific bot reply.",
    )
    def patch(self, request, message_id):
        message = get_object_or_404(
            Message, id=message_id, role=Message.Role.ASSISTANT
        )
        serializer = MessageFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message.feedback = serializer.validated_data["feedback"]
        message.save(update_fields=["feedback"])
        return Response(MessageSerializer(message).data, status=status.HTTP_200_OK)