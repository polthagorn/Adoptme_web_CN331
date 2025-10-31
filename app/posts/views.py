from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'posts/index.html')
def about(request):
    return render(request, 'posts/about.html')
def post(request):
    return render(request, 'posts/posts.html')