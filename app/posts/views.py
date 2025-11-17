from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render, reverse

from .forms import CommentForm, PostForm
from .models import Comment, Post



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
# POST LIST + TAG FILTER
# ----------------------------------------
def post(request):
    tag_filter = request.GET.get('tag', None)

    if tag_filter and tag_filter != "none":
        posts = Post.objects.filter(tag=tag_filter).order_by('-created_at')
    else:
        posts = Post.objects.all().order_by('-created_at')

    return render(request, 'posts/list_posts.html', {
        'posts': posts,
        'selected_tag': tag_filter
    })


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

            # If shelter and approved, attach shelter
            if hasattr(request.user, 'shelter_profile') and request.user.shelter_profile.status == 'APPROVED':
                post.shelter = request.user.shelter_profile

            post.save()
            messages.success(request, "Post created successfully!")
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
            messages.success(request, "Post updated successfully!")
            return redirect('posts')
    else:
        form = PostForm(instance=post)

    return render(request, 'posts/edit_post.html', {'form': form, 'post': post})



# ----------------------------------------
# POST DETAIL + COMMENTS + LIKE + BOOKMARK
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
            return HttpResponseRedirect(request.path_info)

    else:
        comment_form = CommentForm()

    # Like / Bookmark UI state
    is_liked = False
    is_bookmarked = False

    if request.user.is_authenticated:
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

    if request.user != post.author and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this post.")
        return redirect('posts')

    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post deleted successfully!")
        return redirect('posts')

    return render(request, 'posts/delete_post.html', {'post': post})


# ----------------------------------------
# LIKE POST
# ----------------------------------------
@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('posts')))


# ----------------------------------------
# BOOKMARK POST
# ----------------------------------------
@login_required
def bookmark_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.bookmarks.filter(id=request.user.id).exists():
        post.bookmarks.remove(request.user)
    else:
        post.bookmarks.add(request.user)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('posts')))
