# stores/views.py

from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseForbidden, JsonResponse
from django.db import models
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import json
from django.utils.safestring import mark_safe
from app.accounts.models import Notification
from django.db.models.signals import pre_save
from django.dispatch import receiver
from app.accounts.models import Notification

from .models import (
    Store, 
    Product, 
    StoreReview, 
    ProductReview, 
    Cart, 
    CartItem,
    Order,
    OrderItem,
    Payment,
)

from .forms import (
    StoreRequestForm,
    ProductForm,
    StoreUpdateForm,
    StoreReviewForm,
    ProductReviewForm,
    AddToCartForm,
    PaymentForm,    
    OrderStatusUpdateForm,
    OrderShippingForm,
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
            .filter(
                store__status='APPROVED', 
                stock__gt=0
            )
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

        if search_query:    # pragma: no cover
            products_queryset = products_queryset.filter(name__icontains=search_query)

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
        #  รับ order_id จาก URL
        self.order = get_object_or_404(Order, pk=self.kwargs['order_id'], user=request.user)

        #  เช็คว่าเคยรีวิว "สินค้านี้ ในออเดอร์นี้" หรือยัง
        if ProductReview.objects.filter(product=self.product, author=request.user, order=self.order).exists():
            messages.error(request, 'You have already reviewed this product for this order.')
            return redirect('my_order_detail', pk=self.order.pk)
            
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.product = self.product
        #  บันทึก Order ลงไปในรีวิว
        form.instance.order = self.order
        
        messages.success(self.request, 'Your review has been submitted successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_object'] = self.product
        context['review_type'] = 'Product'
        return context

    def get_success_url(self):
        # รีวิวเสร็จ ให้กลับไปหน้า Order Detail เดิม
        return reverse('my_order_detail', kwargs={'pk': self.order.pk})

# ----------------------------------------
# Cart Functionality
# ----------------------------------------

# 1. View สำหรับแสดงหน้ารายละเอียดสินค้า (แก้ไข ProductDetailView เดิม)
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
        
        # ส่ง Form ไปที่ Template
        context['add_to_cart_form'] = AddToCartForm()
        return context

# 2. Function View สำหรับ Logic การเพิ่มลงตะกร้า
@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            
            # Check Stock
            if product.stock < quantity:
                messages.error(request, f"Sorry, only {product.stock} items left in stock.")
                return redirect('product_detail', pk=pk)

            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
            
            if not item_created:
                if (cart_item.quantity + quantity) > product.stock:
                     messages.error(request, "Cannot add more than available stock.")
                     return redirect('product_detail', pk=pk)
                cart_item.quantity += quantity
                cart_item.save()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            
            # ✅ สร้างข้อความแจ้งเตือนแบบมีลิงก์ (ใช้ mark_safe)
            msg = f"Added <b>{product.name}</b> to basket. <a href='{reverse('cart_detail')}' class='underline font-bold ml-2'>View Basket</a>"
            messages.success(request, mark_safe(msg))
            
            # ✅ Redirect กลับไปหน้าเดิม (Product Detail)
            return redirect('product_detail', pk=pk)
            
    return redirect('product_detail', pk=pk)

@login_required
@require_POST
def update_cart_quantity(request, pk):
    try:
        data = json.loads(request.body)
        action = data.get('action') # 'increase' or 'decrease'
        
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        
        if action == 'increase':
            if item.quantity < item.product.stock:
                item.quantity += 1
                item.save()
            else:
                return JsonResponse({'success': False, 'error': 'Max stock reached'})
                
        elif action == 'decrease':
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                # ถ้าลดเหลือ 0 ให้ลบออกเลย หรือจะห้ามลดก็ได้ (ในที่นี้ห้ามลดต่ำกว่า 1)
                return JsonResponse({'success': False, 'error': 'Minimum quantity is 1'})

        # คำนวณยอดรวมใหม่ส่งกลับไป
        cart = item.cart
        selected_items = cart.items.filter(is_selected=True)
        new_total = sum(i.total_price for i in selected_items)
        new_count = sum(i.quantity for i in selected_items)
        
        return JsonResponse({
            'success': True,
            'item_quantity': item.quantity,
            'item_total': float(item.total_price), # ราคารวมของสินค้านั้นๆ (ราคา x จำนวน)
            'cart_total': float(new_total),        # ราคารวมทั้งตะกร้า
            'cart_count': new_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# 3. View สำหรับดูตะกร้าสินค้า
@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    all_items = cart.items.select_related('product', 'product__store').all()

    # 1. แยกประเภทสินค้าตามร้านค้า (PET vs SUPPLIES)
    pet_items = all_items.filter(product__store__store_type='PET')
    supply_items = all_items.filter(product__store__store_type='SUPPLIES')

    # 2. ฟังก์ชันช่วยจัดกลุ่มสินค้าตามร้านค้า
    def group_by_store(items):
        store_dict = {}
        for item in items:
            store = item.product.store
            if store not in store_dict:
                store_dict[store] = []
            store_dict[store].append(item)
        return store_dict.items() # คืนค่าเป็น list of tuples [(store, [items]), ...]

    grouped_pets = group_by_store(pet_items)
    grouped_supplies = group_by_store(supply_items)

    # 3. คำนวณราคารวมเฉพาะรายการที่ถูกเลือก (is_selected=True)
    selected_total = sum(item.total_price for item in all_items if item.is_selected)
    selected_count = sum(item.quantity for item in all_items if item.is_selected)

    context = {
        'cart': cart,
        'grouped_pets': grouped_pets,         # ส่งไปแสดงใน Tab สัตว์เลี้ยง
        'grouped_supplies': grouped_supplies, # ส่งไปแสดงใน Tab ของใช้
        'selected_total': selected_total,
        'selected_count': selected_count,
    }
    return render(request, 'stores/cart_detail.html', context)

# Toggle Checkbox
@login_required
@require_POST
def toggle_cart_item(request, pk):
    try:
        data = json.loads(request.body)
        is_selected = data.get('is_selected', True)
        
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        item.is_selected = is_selected
        item.save()
        
        # คำนวณยอดรวมใหม่ส่งกลับไปอัปเดตหน้าเว็บทันที
        cart = item.cart
        new_total = sum(i.total_price for i in cart.items.filter(is_selected=True))
        new_count = sum(i.quantity for i in cart.items.filter(is_selected=True))
        
        return JsonResponse({
            'success': True, 
            'new_total': float(new_total),
            'new_count': new_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
# 4. View สำหรับลบสินค้าออกจากตะกร้า
@login_required
def remove_from_cart(request, pk):
    cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from basket.")
    return redirect('cart_detail')

# ----------------------------------------
# Order Functionality   
# ----------------------------------------
# 1. Customer: Checkout สินค้าในตะกร้า
@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    selected_items = cart.items.filter(is_selected=True)
    
    if not selected_items.exists():
        messages.error(request, "No items selected for checkout.")
        return redirect('cart_detail')

    # ตรวจสอบ Stock ก่อนสร้าง Order (Double Check)
    for item in selected_items:
        if item.quantity > item.product.stock:
            messages.error(request, f"Product {item.product.name} has only {item.product.stock} left.")
            return redirect('cart_detail')

    # จัดกลุ่มสินค้าตามร้านค้า
    store_items = {}
    for item in selected_items:
        if item.product.store not in store_items:
            store_items[item.product.store] = []
        store_items[item.product.store].append(item)

    for store, items in store_items.items():
        total_price = sum(item.total_price for item in items)
        
        order = Order.objects.create(
            user=request.user,
            store=store,
            total_price=total_price,
            status='PENDING'
        )
        
        for item in items:
            # ✅ ตัด Stock ตรงนี้
            product = item.product
            product.stock -= item.quantity
            product.save()

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price=product.price
            )
            item.delete()

        # 🔔 แจ้งเตือนร้านค้า (กดแล้วไปหน้าจัดการออเดอร์)
        manage_url = reverse('store_order_manage', args=[order.id])
        msg = f"New order #{order.id} from {request.user.username}. <a href='{manage_url}' class='text-accent font-bold hover:underline ml-1'>Manage Order</a>"
        
        Notification.objects.create(
            user=store.owner,
            actor=request.user,
            notification_type='system',
            message=msg
        )

    messages.success(request, "Order placed successfully!")
    return redirect('my_order_list')


# 2. Customer: ดูรายการสั่งซื้อของฉัน
class MyOrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'stores/my_order_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        # ดึงออเดอร์ของฉัน
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        
        # รับค่า status จาก URL มากรอง
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter != 'ALL':
            queryset = queryset.filter(status=status_filter)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ส่งค่า status ปัจจุบันไปที่ Template เพื่อทำปุ่ม Active
        context['current_status'] = self.request.GET.get('status', 'ALL')
        return context


# 3. Customer: หน้าแจ้งชำระเงิน (Payment)
@login_required
def order_payment(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.order = order
            payment.save()
            
            # อัปเดตสถานะ Order
            order.status = 'PAID'
            order.save()
            
            # 🔔 แจ้งเตือนร้านค้า
            manage_url = reverse('store_order_manage', args=[order.id])
            msg = f"Payment submitted for Order #{order.id}. <a href='{manage_url}' class='text-accent font-bold hover:underline ml-1'>Check Payment</a>"

            Notification.objects.create(
                user=order.store.owner,
                actor=request.user,
                notification_type='system',
                message=msg
            )
            
            messages.success(request, "Payment submitted successfully!")
            return redirect('my_order_list')
    else:
        form = PaymentForm(initial={'amount': order.total_price})

    return render(request, 'stores/order_payment.html', {
        'order': order,
        'form': form
    })


# 4. Store Owner: ดูรายการออเดอร์ที่เข้ามา
class StoreOrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'stores/store_order_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        # เริ่มต้นดึงออเดอร์ทั้งหมดของร้าน
        queryset = Order.objects.filter(store__owner=self.request.user).order_by('-created_at')
        
        # ✅ รับค่า status จาก URL (เช่น ?status=PAID)
        status_filter = self.request.GET.get('status')
        
        # ถ้ามีการส่งค่ามา และไม่ใช่ 'ALL' ให้กรอง
        if status_filter and status_filter != 'ALL':
            queryset = queryset.filter(status=status_filter)
            
        return queryset

    # ส่งค่า status ปัจจุบันไปที่ Template เพื่อทำปุ่ม Active
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', 'ALL')
        return context


# 5. Store Owner: จัดการออเดอร์ (ดูรายละเอียด + เปลี่ยนสถานะ)
@login_required
def store_order_manage(request, pk):
    order = get_object_or_404(Order, pk=pk, store__owner=request.user)
    
    if request.method == 'POST':
        # ✅ แก้ไขจุดที่ 1: เก็บสถานะเก่าไว้ "ก่อน" ที่จะสร้าง Form หรือ Validate
        # เพราะถ้าไปเก็บหลัง form.is_valid() ค่าในตัวแปร order จะถูกเปลี่ยนเป็นค่าใหม่ไปแล้ว
        old_status = order.status 

        form = OrderShippingForm(request.POST, request.FILES, instance=order)
        
        if form.is_valid():
            order = form.save()
            
            # ✅ เช็คว่าสถานะเปลี่ยนหรือไม่? (ค่าใหม่ vs ค่าเก่าที่เก็บไว้ตอนแรก)
            if order.status != old_status:
                # สร้างลิงก์ไปหน้า My Order Detail ของลูกค้า
                customer_url = reverse('my_order_detail', args=[order.id])
                
                # สร้างข้อความแจ้งเตือน
                msg = f"Your Order #{order.id} is now <b>{order.get_status_display()}</b>."
                
                if order.status == 'SHIPPED':
                    msg += f" Tracking: {order.tracking_number}"
                
                # ใส่ลิงก์ให้ลูกค้ากด
                msg += f" <a href='{customer_url}' class='text-accent font-bold hover:underline ml-1'>View Details</a>"

                # สร้าง Notification
                Notification.objects.create(
                    user=order.user,    # ส่งหาลูกค้า
                    actor=request.user, # ผู้กระทำคือพ่อค้า
                    notification_type='system',
                    message=msg
                )
            
            messages.success(request, "Order updated successfully.")
            return redirect('store_order_list')
    else:
        form = OrderShippingForm(instance=order)

    return render(request, 'stores/store_order_manage.html', {
        'order': order,
        'form': form
    })

@login_required
def my_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # กรณีขอยกเลิก (ต้องยังไม่จ่ายเงิน - PENDING เท่านั้น)
        if action == 'cancel' and order.status == 'PENDING':
            order.status = 'CANCELLED'
            order.save()
            
            # ✅ คืน Stock สินค้า
            for item in order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
                
            messages.success(request, "Order cancelled. Stock has been restored.")
            return redirect('my_order_detail', pk=pk)

        # กรณีได้รับของแล้ว (ต้องส่งของแล้ว - SHIPPED เท่านั้น)
        elif action == 'receive' and order.status == 'SHIPPED':
            order.status = 'COMPLETED'
            order.save()
            
            # 🔔 แจ้งเตือนร้านค้า
            manage_url = reverse('store_order_manage', args=[order.id])
            msg = f"Order #{order.id} has been received by the customer. <a href='{manage_url}' class='text-accent font-bold hover:underline ml-1'>View Order</a>"
            
            Notification.objects.create(
                user=order.store.owner,
                actor=request.user,
                notification_type='system',
                message=msg
            )

            messages.success(request, "Order completed! You can now review your items.")
            return redirect('my_order_detail', pk=pk)

    reviewed_product_ids = ProductReview.objects.filter(
        author=request.user,
        order=order  # กรองเฉพาะรีวิวที่ผูกกับออเดอร์นี้
    ).values_list('product_id', flat=True)

    return render(request, 'stores/my_order_detail.html', {
        'order': order,
        'reviewed_product_ids': reviewed_product_ids
    })

@receiver(pre_save, sender=Store)
def store_status_notification(sender, instance, **kwargs):
    if instance.pk: # ตรวจสอบว่าเป็นร้านที่มีอยู่แล้ว (ไม่ใช่การสร้างใหม่)
        try:
            old_store = Store.objects.get(pk=instance.pk)
            
            # เช็คว่าสถานะเปลี่ยนจาก PENDING เป็นอย่างอื่นหรือไม่
            if old_store.status == 'PENDING' and instance.status != 'PENDING':
                
                message = ""
                if instance.status == 'APPROVED':
                    message = f"🎉 Your store <b>{instance.name}</b> has been <b>APPROVED</b>! You can now start selling."
                elif instance.status == 'REJECTED':
                    message = f"❌ Your store <b>{instance.name}</b> has been <b>REJECTED</b>. Please contact admin for details."
                
                if message:
                    Notification.objects.create(
                        user=instance.owner,  # ส่งให้เจ้าของร้าน
                        actor=None,           # เป็น System Notification (ไม่มีคนกระทำ)
                        notification_type='system',
                        message=message
                    )
                    
        except Store.DoesNotExist:
            pass
