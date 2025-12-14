from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q

from app.shelters.models import ShelterProfile
from app.stores.models import Store
from app.accounts.models import Profile


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)


# ----------------------------
# Dashboard Home
# ----------------------------
@superuser_required
def dashboard_home(request):
    total_users = User.objects.count()
    total_shelters = ShelterProfile.objects.count()
    pending_shelter_approvals = ShelterProfile.objects.filter(status="PENDING").count()
    pending_store_approvals = Store.objects.filter(status="PENDING").count()

    return render(request, "dashboard/index.html", {
        "total_users": total_users,
        "total_shelters": total_shelters,
        "pending_shelter_approvals": pending_shelter_approvals,
        "pending_store_approvals": pending_store_approvals,
    })


# ----------------------------
# Shelters
# ----------------------------
@superuser_required
def shelter_approval(request):
    shelters = ShelterProfile.objects.filter(status="PENDING")
    return render(request, "dashboard/shelter_approval.html", {"shelters": shelters})


@superuser_required
def approve_shelter(request, shelter_id):
    if request.method != "POST":
        return redirect("shelter_approval")

    shelter = get_object_or_404(ShelterProfile, id=shelter_id)
    shelter.status = "APPROVED"
    shelter.rejection_reason = ""
    shelter.save()

    messages.success(request, f"Shelter '{shelter.name}' approved.")
    return redirect("shelter_approval")


@superuser_required
def reject_shelter(request, shelter_id):
    if request.method != "POST":
        return redirect("shelter_approval")

    shelter = get_object_or_404(ShelterProfile, id=shelter_id)
    reason = (request.POST.get("reason") or "").strip()

    shelter.status = "REJECTED"
    shelter.rejection_reason = reason
    shelter.save()

    messages.error(request, f"Shelter '{shelter.name}' has been rejected.")
    return redirect("shelter_approval")


# ----------------------------
# Users
# ----------------------------
@superuser_required
def user_list(request):
    """
    Supports:
      - ?q= search username/email
      - ?status=all|active|banned|staff|superuser
    """
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "all").strip().lower()

    users = User.objects.all()

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )

    if status == "active":
        users = users.filter(is_active=True)
    elif status == "banned":
        users = users.filter(is_active=False)
    elif status == "staff":
        users = users.filter(is_staff=True)
    elif status == "superuser":
        users = users.filter(is_superuser=True)

    users = users.order_by("-date_joined")

    # Optional: ensure Profile exists for users shown (safe, but can be heavy if many users)
    # for u in users:
    #     Profile.objects.get_or_create(user=u)

    return render(request, "dashboard/user_list.html", {
        "users": users,
        "q": q,
        "status": status,
    })


@superuser_required
def delete_user(request, user_id):
    if request.method != "POST":
        return redirect("dashboard_users")

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("dashboard_users")

    if user.is_superuser:
        messages.error(request, "You cannot delete another admin.")
        return redirect("dashboard_users")

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect("dashboard_users")


@superuser_required
def update_user_score(request, user_id):
    if request.method != "POST":
        return redirect("dashboard_users")

    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        messages.error(request, "You cannot change an admin's score.")
        return redirect("dashboard_users")

    profile, _ = Profile.objects.get_or_create(user=user)

    score_str = (request.POST.get("score") or "").strip()
    try:
        new_score = int(score_str)
    except ValueError:
        messages.error(request, "Score must be a number.")
        return redirect("dashboard_users")

    # clamp (edit as you like)
    new_score = max(0, min(1000, new_score))

    profile.score = new_score
    profile.save()

    messages.success(request, f"{user.username}'s reputation score updated to {new_score}.")
    return redirect("dashboard_users")


@superuser_required
def ban_user(request, user_id):
    if request.method != "POST":
        return redirect("dashboard_users")

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "You cannot ban your own account.")
        return redirect("dashboard_users")

    if user.is_superuser:
        messages.error(request, "You cannot ban another admin.")
        return redirect("dashboard_users")

    user.is_active = False
    user.save()

    # Optional: also reduce score on ban (edit/remove if you don't want this)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.score = max(0, min(1000, profile.score - 50))
    profile.save()

    messages.success(request, f"{user.username} has been banned (disabled).")
    return redirect("dashboard_users")


@superuser_required
def unban_user(request, user_id):
    if request.method != "POST":
        return redirect("dashboard_users")

    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()

    messages.success(request, f"{user.username} has been unbanned (enabled).")
    return redirect("dashboard_users")


# ----------------------------
# Stores
# ----------------------------
@superuser_required
def store_approval(request):
    stores = Store.objects.filter(status="PENDING")
    return render(request, "dashboard/store_approval.html", {"stores": stores})


@superuser_required
def approve_store(request, store_id):
    if request.method != "POST":
        return redirect("store_approval")

    store = get_object_or_404(Store, id=store_id)
    store.status = "APPROVED"
    store.save()

    messages.success(request, f"Store '{store.name}' approved.")
    return redirect("store_approval")


@superuser_required
def reject_store(request, store_id):
    if request.method != "POST":
        return redirect("store_approval")

    store = get_object_or_404(Store, id=store_id)
    store.status = "REJECTED"
    store.save()

    messages.error(request, f"Store '{store.name}' rejected.")
    return redirect("store_approval")
