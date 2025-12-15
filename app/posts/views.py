import math

from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.http import HttpResponseForbidden
from app.accounts.models import Notification
from .models import Post
from .forms import PostForm, CommentForm



# ----------------------------------------
# PUBLIC PAGES
# ----------------------------------------
def welcome(request):
    return render(request, 'posts/welcome.html')


def home(request):
    return render(request, 'posts/index.html')


def about(request):
    return render(request, 'posts/about.html')


# ----------------------------------------
# POST LIST + TAG + ANIMAL FILTER + LOCATION FILTER
# ----------------------------------------
def post(request):
    # ------- basic filters from query string -------
    tag_filter = request.GET.get('tag', None)
    animal_type_filter = request.GET.get('animal_type', None)
    animal_race_filter = request.GET.get('animal_race', None)

    # base queryset
    posts_qs = Post.objects.all()

    # TAG FILTER
    if tag_filter and tag_filter != "none":
        posts_qs = posts_qs.filter(tag=tag_filter)

    # 🐾 ANIMAL TYPE FILTER
    if animal_type_filter and animal_type_filter not in ["", "all", "None"]:
        posts_qs = posts_qs.filter(animal_type=animal_type_filter)

    # 🐾 ANIMAL RACE / BREED FILTER
    if animal_race_filter and animal_race_filter not in ["", "all", "None"]:
        posts_qs = posts_qs.filter(animal_race=animal_race_filter)

    # -------- LOCATION FILTER INPUTS --------
    center_lat = request.GET.get('center_lat')
    center_lng = request.GET.get('center_lng')
    radius_km = request.GET.get('radius_km')
    location_active = False

    posts = list(posts_qs.order_by('-created_at'))

    if center_lat and center_lng and radius_km:
        try:
            center_lat = float(center_lat)
            center_lng = float(center_lng)
            radius_km = float(radius_km)
            location_active = radius_km > 0
        except ValueError:
            location_active = False

    if location_active:
        def haversine(lat1, lon1, lat2, lon2):
            """Return distance in km between 2 lat/lng points."""
            R = 6371.0
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)

            a = (math.sin(dphi / 2) ** 2 +
                 math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        filtered = []
        for p in posts:
            if p.latitude is not None and p.longitude is not None:
                d = haversine(center_lat, center_lng, p.latitude, p.longitude)
                if d <= radius_km:
                    # attach distance for display
                    p.distance_km = round(d, 1)
                    filtered.append(p)

        # sort by distance
        posts = sorted(filtered, key=lambda x: x.distance_km)

    context = {
        'posts': posts,

        # tag
        'selected_tag': tag_filter,

        # 🐾 animal filters (for keeping dropdown state)
        'selected_animal_type': animal_type_filter,
        'selected_animal_race': animal_race_filter,

        # location
        'center_lat': center_lat if location_active else '',
        'center_lng': center_lng if location_active else '',
        'radius_km': radius_km if location_active else '',
        'location_active': location_active,
    }

    return render(request, 'posts/list_posts.html', context)


# ----------------------------------------
# CREATE POST (USER + SHELTER SUPPORT)
# ----------------------------------------
@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            
            is_shelter_post = False

            # เช็ค Shelter และ Assign
            if hasattr(request.user, 'shelter_profile') and request.user.shelter_profile.status == 'APPROVED':
                post.shelter = request.user.shelter_profile
                is_shelter_post = True

            post.save() # Save ก่อนเพื่อให้มี post.id

            # Logic แจ้งเตือนแบบมีลิงก์กด 
            if is_shelter_post:
                followers = post.shelter.followers.all()
                
                # สร้าง URL สำหรับไปหน้า Post Detail
                post_url = reverse('post_detail', args=[post.id])
                
                for follower in followers:
                    if follower != request.user:
                        # สร้างข้อความแบบ HTML ตามสไตล์ที่คุณต้องการ
                        msg = f"<b>{post.shelter.name}</b> has posted a new update: {post.title}. <a href='{post_url}' class='text-accent font-bold hover:underline ml-1'>View Post</a>"
                        
                        Notification.objects.create(
                            user=follower,
                            actor=request.user,
                            notification_type='system',
                            message=msg,
                            post=post # ใส่ไว้ด้วยเผื่อใช้ในอนาคต
                        )

            return redirect('posts')
    else:
        form = PostForm()

    return render(request, 'posts/create_post.html', {'form': form})


# ----------------------------------------
# EDIT POST
# ----------------------------------------
@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            form.save()
            return redirect('posts')
    else:
        form = PostForm(instance=post)

    return render(request, 'posts/edit_post.html', {
        'form': form,
        'post': post
    })


# ----------------------------------------
# POST DETAIL + COMMENTS
# ----------------------------------------
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()

    # POST request = comment submit
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.author = request.user
            new_comment.save()

            # 🔔 NOTIFICATION FOR COMMENT (only if not commenting on own post)
            if request.user != post.author:
                Notification.objects.create(
                    user=post.author,           # who receives the noti
                    actor=request.user,         # who did the action
                    notification_type="comment",
                    message=f"{request.user.username} commented on your post.",
                    post=post,
                )

            return HttpResponseRedirect(request.path_info)
    else:
        comment_form = CommentForm()

    # Like / Bookmark UI state
    is_liked = False
    is_bookmarked = False

    if request.user.is_authenticated: # pragma: no cover
        is_liked = post.likes.filter(id=request.user.id).exists()
        is_bookmarked = post.bookmarks.filter(id=request.user.id).exists()

    return render(request, 'posts/detail_post.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': is_liked,
        'is_bookmarked': is_bookmarked
    })


# ----------------------------------------
# DELETE POST
# ----------------------------------------
@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.author and not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("You don't have permission to delete this post.")

    if request.method == 'POST':
        post.delete()
        return redirect('posts')

    return render(request, 'posts/delete_post.html', {'post': post})


# ----------------------------------------
# LIKE POST (AJAX)
# ----------------------------------------
@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.likes.filter(id=request.user.id).exists():
        # already liked → unlike
        post.likes.remove(request.user)
        liked = False
    else:
        # not liked → add like
        post.likes.add(request.user)
        liked = True

        # 🔔 NOTIFICATION FOR LIKE (only if not liking own post)
        if request.user != post.author:
            Notification.objects.create(
                user=post.author,           # who receives the noti
                actor=request.user,         # who did the action
                notification_type="like",
                message=f"{request.user.username} liked your post.",
                post=post,
            )

    # ✅ Return JSON instead of Redirect
    return JsonResponse({
        'liked': liked,
        'count': post.likes.count()
    })


# ----------------------------------------
# BOOKMARK POST (AJAX)
# ----------------------------------------
@login_required
def bookmark_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.bookmarks.filter(id=request.user.id).exists():
        post.bookmarks.remove(request.user)
        bookmarked = False
    else:
        post.bookmarks.add(request.user)
        bookmarked = True

    # ✅ Return JSON instead of Redirect
    return JsonResponse({
        'bookmarked': bookmarked
    })