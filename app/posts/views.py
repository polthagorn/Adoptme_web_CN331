from django.shortcuts import render, redirect,get_object_or_404, reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .models import Post, Comment
from .forms import PostForm, CommentForm

def welcome(request):
    return render(request, 'posts/welcome.html')

def home(request):
    return render(request, 'posts/index.html')

def about(request):
    return render(request, 'posts/about.html')

def post(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'posts/list_posts.html', {'posts': posts})

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts')
    else:
        form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})

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

    return render(request, 'posts/edit_post.html', {'form': form, 'post': post})

def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()
    
    # --- comment ---
    if request.method == 'POST':
        # check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('login')
            
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.author = request.user
            new_comment.save()
            return HttpResponseRedirect(request.path_info)
    else:
        comment_form = CommentForm()

    # --- like/bookmarks ---
    is_liked = False
    is_bookmarked = False
    if request.user.is_authenticated:
        is_liked = post.likes.filter(id=request.user.id).exists()
        is_bookmarked = post.bookmarks.filter(id=request.user.id).exists()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': is_liked,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'posts/detail_post.html', context)

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        post.delete()
        return redirect('posts')
    return render(request, 'posts/delete_post.html', {'post': post})


'''shelter post creation view'''
@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            
            # check if the user has an approved shelter profile
            if hasattr(request.user, 'shelter_profile') and request.user.shelter_profile.status == 'APPROVED':
                post.shelter = request.user.shelter_profile
            
            post.save()
            return redirect('posts')
    else:
        form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('posts')))

# --- Bookmark/Unbookmark ---
@login_required
def bookmark_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.bookmarks.filter(id=request.user.id).exists():
        post.bookmarks.remove(request.user)
    else:
        post.bookmarks.add(request.user)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('posts')))