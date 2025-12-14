from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse

from .models import Conversation, Message

User = get_user_model()


@login_required
def inbox(request):
    q = (request.GET.get("q") or "").strip()

    # Conversations for this user
    conversations = (
        Conversation.objects
        .filter(participants=request.user)
        .order_by("-updated_at", "-id")
        .prefetch_related("participants")
    )

    conv_data = []
    for c in conversations:
        # who is the other person in this DM (assumes 2 participants)
        other = c.participants.exclude(id=request.user.id).first()

        # unread = messages from other people AND not read by me
        unread_count = (
            c.messages
            .exclude(sender=request.user)
            .exclude(read_by=request.user)
            .count()
        )

        conv_data.append((c, other, unread_count))

    # Search users to start DM
    users = []
    if q:
        users = (
            User.objects
            .filter(username__icontains=q)
            .exclude(id=request.user.id)[:10]
        )

    return render(request, "chat/inbox.html", {
        "conv_data": conv_data,  # now has (conv, other, unread)
        "users": users,
        "q": q,
    })


@login_required
def thread(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, participants=request.user)

    # Get messages
    msgs = conv.messages.select_related("sender").all()

    # Mark incoming messages as read by current user
    for m in msgs.exclude(sender=request.user):
        if not m.read_by.filter(id=request.user.id).exists():
            m.read_by.add(request.user)

    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            Message.objects.create(
                conversation=conv,
                sender=request.user,
                body=body
            )
            conv.save()  # updates updated_at
        return redirect("chat_thread", pk=conv.pk)

    # send other user too (useful for thread header)
    other = conv.participants.exclude(id=request.user.id).first()

    return render(request, "chat/thread.html", {
        "conv": conv,
        "msgs": msgs,
        "other": other,
    })


@login_required
def start_dm(request, user_id):
    other = get_object_or_404(User, pk=user_id)
    if other == request.user:
        return redirect("chat_inbox")

    # Your model should implement this:
    # Conversation.get_or_create_dm(user1, user2) -> (conversation, created)
    conv, _ = Conversation.get_or_create_dm(request.user, other)
    return redirect("chat_thread", pk=conv.pk)

@login_required
def unread_counts(request):
    # total unread across all conversations
    total_unread = (
        Message.objects
        .filter(conversation__participants=request.user)
        .exclude(sender=request.user)
        .exclude(read_by=request.user)
        .count()
    )

    # unread per conversation (for inbox)
    per_conv = (
        Message.objects
        .filter(conversation__participants=request.user)
        .exclude(sender=request.user)
        .exclude(read_by=request.user)
        .values("conversation_id")
        .annotate(unread=Count("id"))
    )

    return JsonResponse({
        "total_unread": total_unread,
        "per_conversation": {str(x["conversation_id"]): x["unread"] for x in per_conv},
    })