# stores/views.py

from django.shortcuts import get_object_or_404, redirect
from django.db.models import Avg
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden
from django.db import models
from django.contrib import messages

from .models import Store, Product, StoreReview, ProductReview
from .forms import (
    StoreRequestForm,
    ProductForm,
    StoreUpdateForm,
    StoreReviewForm,
    ProductReviewForm,
)


class StoreRequestCreateView(LoginRequiredMixin, CreateView):
    model = Store
    form_class = StoreRequestForm
    template_name = 'stores/store_request_form.html'
    success_url = reverse_lazy('store_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MyStoreListView(LoginRequiredMixin, ListView):
    model = Store
    template_name = 'stores/my_store_list.html'
    context_object_name = 'my_stores'

    def get_queryset(self):
        return Store.objects.filter(owner=self.request.user).order_by('-created_at')


class StoreProfileView(DetailView):
    model = Store
    template_name = 'stores/store_profile.html'
    context_object_name = 'store'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.get_object()
        reviews = store.reviews.all()
        context['products'] = Product.objects.filter(
            store=store,
            store__status='APPROVED'
        ).order_by('-created_at')
        context['reviews'] = reviews
        context['average_rating'] = reviews.aggregate(Avg('rating'))['rating__avg']
        return context


class MarketplaceView(ListView):
    model = Product
    template_name = 'stores/marketplace.html'
    context_object_name = 'products'
    paginate_by = 12

    # ✅ allowed sort keys (safe whitelist)
    SORT_OPTIONS = {
        "new": "-created_at",
        "old": "created_at",
        "price_low": "price",
        "price_high": "-price",
        "name_az": "name",
        "name_za": "-name",
        "rating_high": "-avg_rating",
    }

    def get_queryset(self):
        queryset = (
            Product.objects
            .filter(store__status='APPROVED')
            .select_related('store')
        )

        search_query = self.request.GET.get('q', None)
        store_type = self.request.GET.get('type', None)
        sort_key = self.request.GET.get('sort', 'new')

        # ✅ search
        if search_query:
            queryset = queryset.filter(
                models.Q(name__icontains=search_query) |
                models.Q(description__icontains=search_query) |
                models.Q(store__name__icontains=search_query)
            )

        # ✅ type filter
        if store_type in ['PET', 'SUPPLIES']:
            queryset = queryset.filter(store__store_type=store_type)

        # ✅ rating sort needs annotate
        if sort_key == "rating_high":
            queryset = queryset.annotate(avg_rating=Avg("reviews__rating"))

        # ✅ apply sort (fallback to newest)
        order_by = self.SORT_OPTIONS.get(sort_key, "-created_at")

        # tie-breaker to keep stable ordering
        if sort_key == "rating_high":
            return queryset.order_by(order_by, "-created_at")
        return queryset.order_by(order_by, "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        search_query = self.request.GET.get('q', '')
        context['search_query'] = search_query
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_sort'] = self.request.GET.get('sort', 'new')

        found_stores = None
        if search_query:
            found_stores = Store.objects.filter(
                status='APPROVED',
                name__icontains=search_query
            )
        context['found_stores'] = found_stores

        # optional: for dropdown in template
        context['sort_options'] = [
            ("new", "Newest"),
            ("old", "Oldest"),
            ("price_low", "Price: Low → High"),
            ("price_high", "Price: High → Low"),
            ("name_az", "Name: A → Z"),
            ("name_za", "Name: Z → A"),
            ("rating_high", "Top rated"),
        ]
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'stores/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        reviews = product.reviews.all()
        context['reviews'] = reviews
        context['average_rating'] = reviews.aggregate(Avg('rating'))['rating__avg']
        return context


class StoreManageView(LoginRequiredMixin, DetailView):
    model = Store
    template_name = 'stores/store_manage.html'
    context_object_name = 'store'

    def dispatch(self, request, *args, **kwargs):
        store = self.get_object()
        handler = super().dispatch(request, *args, **kwargs)
        if getattr(handler, 'status_code', 200) in (301, 302):
            return handler
        if store.owner != request.user:
            return HttpResponseForbidden("You are not the owner of this store")
        return handler

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.get_object()
        search_query = self.request.GET.get('q', '')
        products_queryset = Product.objects.filter(store=store)

        if search_query:
            products_queryset = products_queryset.filter(name__icontains=search_query)  # pragma: no cover

        context['products'] = products_queryset.order_by('-created_at')
        context['search_query'] = search_query

        reviews = store.reviews.all()
        context['reviews'] = reviews
        context['average_rating'] = reviews.aggregate(Avg('rating'))['rating__avg']
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'stores/product_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.store = get_object_or_404(Store, pk=self.kwargs['pk'])
        handler = super().dispatch(request, *args, **kwargs)
        if getattr(handler, 'status_code', 200) in (301, 302):
            return handler
        if self.store.owner != request.user:
            return HttpResponseForbidden("You are not the owner of this store")
        if self.store.status != 'APPROVED':
            return HttpResponseForbidden("You can only add products to approved stores")
        return handler

    def form_valid(self, form):
        form.instance.store = self.store
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['store'] = self.store
        return context

    def get_success_url(self):
        return reverse('store_manage', kwargs={'pk': self.store.pk})


class StoreUpdateView(LoginRequiredMixin, UpdateView):
    model = Store
    form_class = StoreUpdateForm
    template_name = 'stores/store_update_form.html'
    context_object_name = 'store'

    def get_success_url(self):
        return reverse_lazy('store_manage', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        store = self.get_object()
        handler = super().dispatch(request, *args, **kwargs)
        if getattr(handler, 'status_code', 200) in (301, 302):
            return handler
        if store.owner != request.user:
            return HttpResponseForbidden("You do not have permission to edit this store.")
        return handler


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'stores/product_update_form.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.filter(store__owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['store'] = self.get_object().store
        return context

    def get_success_url(self):
        product = self.get_object()
        return reverse_lazy('store_manage', kwargs={'pk': product.store.pk})


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'stores/product_confirm_delete.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.filter(store__owner=self.request.user)

    def get_success_url(self):
        product = self.get_object()
        return reverse_lazy('store_manage', kwargs={'pk': product.store.pk})


class StoreReviewListView(DetailView):
    """แสดงรายการรีวิวทั้งหมดของร้านค้า"""
    model = Store
    template_name = 'stores/store_review_list.html'
    context_object_name = 'store'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = self.get_object().reviews.all()
        return context


class StoreReviewCreateView(LoginRequiredMixin, CreateView):
    """หน้าฟอร์มสำหรับเขียนรีวิวร้านค้า"""
    model = StoreReview
    form_class = StoreReviewForm
    template_name = 'stores/review_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.store = get_object_or_404(Store, pk=self.kwargs['pk'])
        if StoreReview.objects.filter(store=self.store, author=request.user).exists():
            messages.error(request, 'You have already reviewed this store.')
            return redirect('store_profile', pk=self.store.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.store = self.store
        messages.success(self.request, 'Your review has been submitted successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_object'] = self.store
        context['review_type'] = 'Store'
        return context

    def get_success_url(self):
        return reverse('store_profile', kwargs={'pk': self.store.pk})


class ProductReviewListView(DetailView):
    model = Product
    template_name = 'stores/product_review_list.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reviews'] = self.get_object().reviews.all()
        return context


class ProductReviewCreateView(LoginRequiredMixin, CreateView):
    model = ProductReview
    form_class = ProductReviewForm
    template_name = 'stores/review_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=self.kwargs['pk'])
        if ProductReview.objects.filter(product=self.product, author=request.user).exists():
            messages.error(request, 'You have already reviewed this product.')
            return redirect('product_detail', pk=self.product.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.product = self.product
        messages.success(self.request, 'Your review has been submitted successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_object'] = self.product
        context['review_type'] = 'Product'
        return context

    def get_success_url(self):
        return reverse('product_detail', kwargs={'pk': self.product.pk})
