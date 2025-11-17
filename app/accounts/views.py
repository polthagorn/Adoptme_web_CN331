from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .models import Profile


def login_page(request):
    if request.method == "POST":
        username_or_email = request.POST.get("username_or_email")
        password = request.POST.get("password")

        # Try username first
        user = authenticate(request, username=username_or_email, password=password)

        # If not found, try email
        if user is None:
            try:
                u = User.objects.get(email=username_or_email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            return redirect('/')  # Redirect to homepage
        else:
            messages.error(request, "Wrong username or password")

    return render(request, 'accounts/login_page.html')


def register_page(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        country = request.POST.get('country')
        city = request.POST.get('city')

        # Save user inputs for re-rendering if error
        context = {
            "username": username,
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "country": country,
            "city": city,
        }

        # ----------------------
        # PHONE VALIDATION (NEW)
        # ----------------------
        import re
        phone_pattern = r'^(\+66|0)\d{8,9}$'

        if not re.match(phone_pattern, phone):
            messages.error(request, "Invalid phone number. Please use a valid Thai phone number.")
            return render(request, 'accounts/register_page.html', context)

        # Password match
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'accounts/register_page.html', context)

        # Username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return render(request, 'accounts/register_page.html', context)

        # Email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return render(request, 'accounts/register_page.html', context)

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Create profile
        Profile.objects.create(
            user=user,
            phone=phone,
            country=country,
            city=city
        )

        messages.success(request, "Account created successfully. Please login.")
        return redirect('login')

    return render(request, 'accounts/register_page.html')


def logout_page(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('home')


@login_required
def profile_page(request):
    user = request.user

    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(
            user=user,
            phone="N/A",
            country="N/A",
            city="N/A"
        )

    return render(request, 'accounts/profile_page.html', {'profile': profile})

