from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import Profile

# Create your views here.
def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/")  # redirect to homepage
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

        # Password Match Check
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        # Username Already Exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('register')

        # Create User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Create Profile
        Profile.objects.create(
            user=user,
            phone=phone,
            country=country,
            city=city
        )

        messages.success(request, "Account created successfully. Please login.")
        return redirect('login')

    return render(request, 'accounts/register_page.html')
