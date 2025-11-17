from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .models import Profile
from app.posts.models import Post
from .forms import UserUpdateForm, ProfileUpdateForm
import re


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

@login_required
def profile_edit_page(request):
    if request.method == 'POST':
        if 'remove_image' in request.POST:
            profile = request.user.profile
            profile.image.delete(save=False)
            profile.image = 'default.jpg'    
            profile.save()
            messages.success(request, 'Your profile picture has been removed.')
            return redirect('profile_edit')

        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            new_username = u_form.cleaned_data.get('username')
            
            if User.objects.exclude(pk=request.user.pk).filter(username=new_username).exists():
                u_form.add_error('username', f"Username '{new_username}' is already taken.")
            else:
                u_form.save()
                p_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'accounts/profile_edit_page.html', context)

def user_profile_page(request, username):
    user_obj = get_object_or_404(User, username=username)
    user_posts = Post.objects.filter(author=user_obj).order_by('-created_at')
    
    context = {
        'profile_user': user_obj, 
        'posts': user_posts,
    }
    return render(request, 'accounts/user_profile_page.html', context)

@login_required
def my_bookmarks_page(request):
    bookmarked_posts = request.user.bookmarked_posts.all().order_by('-created_at')
    
    context = {
        'posts': bookmarked_posts
    }
    return render(request, 'accounts/my_bookmarks_page.html', context)