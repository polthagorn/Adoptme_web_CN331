from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from app.chats.models import Conversation, Message

User = get_user_model()


class ChatViewsTest(TestCase):

    def setUp(self):
        # users
        self.user1 = User.objects.create_user(username="alice", password="pass1234")
        self.user2 = User.objects.create_user(username="bob", password="pass1234")

        # login user1
        self.client.login(username="alice", password="pass1234")

    # --------------------
    # Inbox
    # --------------------
    def test_inbox_view_loads(self):
        url = reverse("chat_inbox")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/inbox.html")

    # --------------------
    # Start DM
    # --------------------
    def test_start_dm_creates_conversation(self):
        url = reverse("chat_start_dm", args=[self.user2.id])
        response = self.client.get(url)

        # redirect to thread
        self.assertEqual(response.status_code, 302)

        conv = Conversation.objects.first()
        self.assertIsNotNone(conv)
        self.assertIn(self.user1, conv.participants.all())
        self.assertIn(self.user2, conv.participants.all())

    # --------------------
    # Thread view
    # --------------------
    def test_thread_view_loads(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)

        url = reverse("chat_thread", args=[conv.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/thread.html")

    # --------------------
    # Send message
    # --------------------
    def test_send_message(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)

        url = reverse("chat_thread", args=[conv.id])
        response = self.client.post(url, {"body": "Hello Bob"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.count(), 1)

        msg = Message.objects.first()
        self.assertEqual(msg.body, "Hello Bob")
        self.assertEqual(msg.sender, self.user1)
        self.assertEqual(msg.conversation, conv)

    # --------------------
    # Unread logic
    # --------------------
    def test_unread_message_count(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)

        # bob sends message to alice
        Message.objects.create(
            conversation=conv,
            sender=self.user2,
            body="Hi Alice"
        )

        unread = (
            Message.objects
            .filter(conversation=conv)
            .exclude(sender=self.user1)
            .exclude(read_by=self.user1)
            .count()
        )

        self.assertEqual(unread, 1)

    # --------------------
    # Unread API
    # --------------------
    def test_unread_counts_api(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)

        Message.objects.create(
            conversation=conv,
            sender=self.user2,
            body="Ping"
        )

        url = reverse("chat_unread_counts")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["total_unread"], 1)
        self.assertEqual(data["per_conversation"][str(conv.id)], 1)

class ChatCoverageExtraTests(TestCase): # Extra test for 100%
    def setUp(self):
        self.user1 = User.objects.create_user(username="alice", password="pass1234")
        self.user2 = User.objects.create_user(username="bob", password="pass1234")
        self.client.login(username="alice", password="pass1234")

    # Covers: inbox loop building (other=..., unread_count=..., conv_data.append...)
    def test_inbox_builds_conv_data_and_unread(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)

        # bob sends 2 messages; only 1 is unread for alice
        m1 = Message.objects.create(conversation=conv, sender=self.user2, body="one")
        m2 = Message.objects.create(conversation=conv, sender=self.user2, body="two")
        m1.read_by.add(self.user1)  # mark one as read

        url = reverse("chat_inbox")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # conv_data = [(conv, other, unread)]
        conv_data = resp.context["conv_data"]
        self.assertEqual(len(conv_data), 1)

        c, other, unread = conv_data[0]
        self.assertEqual(c.id, conv.id)
        self.assertEqual(other.id, self.user2.id)
        self.assertEqual(unread, 1)

    # Covers: users search query block in inbox (q provided)
    def test_inbox_search_users(self):
        # create a third user that matches query
        User.objects.create_user(username="bobby", password="pass1234")

        url = reverse("chat_inbox") + "?q=bo"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        users = list(resp.context["users"])
        usernames = [u.username for u in users]

        self.assertIn("bob", usernames)
        self.assertIn("bobby", usernames)
        self.assertNotIn("alice", usernames)  # excluded current user

    # Covers: mark incoming messages as read (for-loop + exists() branch)
    def test_thread_marks_incoming_as_read(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.user1, self.user2)

        msg = Message.objects.create(conversation=conv, sender=self.user2, body="hello")

        # before: alice has not read
        self.assertFalse(msg.read_by.filter(id=self.user1.id).exists())

        url = reverse("chat_thread", args=[conv.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # after: should be marked read
        msg.refresh_from_db()
        self.assertTrue(msg.read_by.filter(id=self.user1.id).exists())

    # Covers: start_dm when user tries to message themself (return redirect("chat_inbox"))
    def test_start_dm_self_redirects_to_inbox(self):
        url = reverse("chat_start_dm", args=[self.user1.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("chat_inbox"))