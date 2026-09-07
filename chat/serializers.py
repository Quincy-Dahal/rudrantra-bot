"""
chat/serializers.py

Two kinds of serializers here, for two different purposes:

- ConversationSerializer / MessageSerializer: read-only views onto the
  actual database models, used when listing/retrieving conversation history.
- ChatRequestSerializer / ChatResponseSerializer: not tied to a model at
  all - they describe the shape of the chat endpoint's request and reply,
  and exist so drf-spectacular can document that endpoint properly in
  Swagger.
"""

from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "feedback", "created_at"]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "created_at", "updated_at", "messages"]
        read_only_fields = fields


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        help_text="The visitor's message to send to the bot.",
    )
    conversation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Omit to start a new conversation. Include to continue an existing one.",
    )


class ChatResponseSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(
        help_text="Pass this back as conversation_id on the next message to continue this conversation."
    )
    message_id = serializers.IntegerField(
        help_text="ID of the bot's reply message - pass this to the feedback endpoint to rate this specific reply."
    )
    reply = serializers.CharField(help_text="The bot's reply.")
    
class MessageFeedbackSerializer(serializers.Serializer):
    feedback = serializers.ChoiceField(
        choices=Message.Feedback.choices,
        allow_null=True,
        help_text="Set to 'up' or 'down' to rate a reply, or null to clear existing feedback.",
    )