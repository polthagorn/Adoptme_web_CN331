from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from app.shelters.models import ShelterProfile
from django.contrib.auth.models import User
from django.contrib import messages
from app.stores.models import Store



def dashboard_home(request):
    return render(request, "dashboard/index.html")

# Allow only superusers to approve shelters
def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

@superuser_required
def shelter_approval(request):
    shelters = ShelterProfile.objects.filter(status='PENDING')
    return render(request, "dashboard/shelter_approval.html", {"shelters": shelters})


@superuser_required
def approve_shelter(request, shelter_id):
    shelter = ShelterProfile.objects.get(id=shelter_id)
    shelter.status = "APPROVED"
    shelter.save()
    return redirect("shelter_approval")


@superuser_required
def reject_shelter(request, shelter_id):
    shelter = ShelterProfile.objects.get(id=shelter_id)
    shelter.status = "REJECTED"
    shelter.save()
    return redirect("shelter_approval")

def dashboard_home(request):
    total_users = User.objects.count()
    total_shelters = ShelterProfile.objects.count()
    pending_shelter_approvals = ShelterProfile.objects.filter(status="PENDING").count()

    return render(request, "dashboard/index.html", {
        "total_users": total_users,
        "total_shelters": total_shelters,
        "pending_shelter_approvals": pending_shelter_approvals,
    })

def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

@superuser_required
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, "dashboard/user_list.html", {
        "users": users
    })

@superuser_required
def delete_user(request, user_id):
    user = User.objects.get(id=user_id)

    # Prevent deleting yourself
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect("dashboard_users")

    # Prevent deleting other superusers
    if user.is_superuser:
        messages.error(request, "You cannot delete another admin.")
        return redirect("dashboard_users")

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect("dashboard_users")

@superuser_required
def store_approval(request):
    stores = Store.objects.filter(status="PENDING")
    return render(request, "dashboard/store_approval.html", {"stores": stores})


@superuser_required
def approve_store(request, store_id):
    store = Store.objects.get(id=store_id)
    store.status = "APPROVED"
    store.save()
    messages.success(request, f"Store '{store.name}' approved.")
    return redirect("store_approval")


@superuser_required
def reject_store(request, store_id):
    store = Store.objects.get(id=store_id)
    store.status = "REJECTED"
    store.save()
    messages.error(request, f"Store '{store.name}' rejected.")
    return redirect("store_approval")