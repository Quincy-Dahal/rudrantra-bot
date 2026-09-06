"""
chat/models.py

Stores chat history. A Conversation groups a sequence of Messages between
a website visitor and the bot; each Message is tagged as either the
visitor's turn (user) or the bot's reply (assistant).
"""

import uuid

from django.db import models


class Conversation(models.Model):
    """
    One chat session. Identified by a UUID (rather than an auto-increment
    integer) so it's safe to hand back to the frontend and use directly in
    the API without revealing how many conversations exist.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation {self.id}"


class Message(models.Model):
    """
    A single turn within a Conversation - either what the visitor typed
    (role=user) or what the model replied (role=assistant).
    """

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        
    class Feedback(models.TextChoices):
        UP = "up", "Thumbs up"
        DOWN = "down", "Thumbs down"


    conversation = models.ForeignKey(
        Conversation, related_name="messages", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    feedback = models.CharField(
        max_length=4,
        choices=Feedback.choices,
        null=True,
        blank=True,
        help_text="Customer's thumbs up/down on this reply, if given.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        preview = self.content[:50]
        return f"[{self.role}] {preview}"