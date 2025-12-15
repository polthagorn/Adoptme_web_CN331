from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import CreateView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden
from .models import ShelterProfile
from .forms import ShelterRegistrationForm, ShelterUpdateForm
from app.posts.models import Post
from app.posts.forms import PostForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from app.accounts.models import Notification

class ShelterRegisterView(LoginRequiredMixin, CreateView):
    model = ShelterProfile
    form_class = ShelterRegistrationForm
    template_name = 'shelters/shelter_register_form.html'
    success_url = reverse_lazy('shelter_profile') 

    def dispatch(self, request, *args, **kwargs):
        # check if the user already has a shelter profile
        if hasattr(request.user, 'shelter_profile'):
            # if yes, redirect to the profile view
            return redirect('shelter_profile')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ShelterProfileView(LoginRequiredMixin, DetailView):
    model = ShelterProfile
    template_name = 'shelters/shelter_profile.html'
    context_object_name = 'shelter'

    def get_object(self, queryset=None):
        return get_object_or_404(ShelterProfile, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shelter = self.get_object()
        context['shelter_posts'] = Post.objects.filter(shelter=shelter).order_by('-created_at')
        return context

    
class ShelterUpdateView(LoginRequiredMixin, UpdateView):
    model = ShelterProfile
    form_class = ShelterUpdateForm
    template_name = 'shelters/shelter_update_form.html'
    success_url = reverse_lazy('shelter_profile') 

    def get_object(self, queryset=None):
        return get_object_or_404(ShelterProfile, user=self.request.user)
    
class PublicShelterProfileView(DetailView):
    model = ShelterProfile
    template_name = 'shelters/public_shelter_profile.html' # สร้าง template ใหม่
    context_object_name = 'shelter'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shelter = self.get_object()
        context['shelter_posts'] = Post.objects.filter(shelter=shelter).order_by('-created_at')
        if self.request.user.is_authenticated:
            context['is_following'] = self.request.user in shelter.followers.all()
        else:
            context['is_following'] = False
            
        return context
    


@login_required
@require_POST
def follow_shelter(request, pk):
    shelter = get_object_or_404(ShelterProfile, pk=pk)
    
    # ป้องกันไม่ให้เจ้าของ Shelter กดติดตามตัวเอง (Optional)
    if shelter.user == request.user:
        return JsonResponse({'error': 'You cannot follow your own shelter.'}, status=403)

    if request.user in shelter.followers.all():
        shelter.followers.remove(request.user)
        is_following = False
    else:
        shelter.followers.add(request.user)
        is_following = True

    # ส่วนแจ้งเตือน 
    if request.user != shelter.user:
        Notification.objects.create(
            user=shelter.user,
            actor=request.user,
            notification_type='system',
            message=f"{request.user.username} started following your shelter."
        )

    return JsonResponse({
        'is_following': is_following,
        'follower_count': shelter.followers.count()
    })
    

