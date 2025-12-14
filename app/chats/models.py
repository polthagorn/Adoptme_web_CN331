from django.conf import settings
from django.db import models
from django.db.models import Q

User = settings.AUTH_USER_MODEL


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation #{self.pk}"

    @staticmethod
    def get_or_create_dm(user_a, user_b):
        """
        Return an existing 2-person conversation if it exists, else create it.
        """
        qs = (Conversation.objects
              .filter(participants=user_a)
              .filter(participants=user_b)
              .distinct())
        # ensure it's a DM (exactly 2 participants)
        for conv in qs:
            if conv.participants.count() == 2:
                return conv, False

        conv = Conversation.objects.create()
        conv.participants.add(user_a, user_b)
        return conv, True

    def other_user(self, me):
        return self.participants.exclude(id=me.id).first()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # unread/read system
    read_by = models.ManyToManyField(User, blank=True, related_name="read_messages")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg #{self.pk} in Conv #{self.conversation_id}"

    def is_read(self, user):
        return self.read_by.filter(id=user.id).exists()
