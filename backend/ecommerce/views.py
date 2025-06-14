from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate # Added authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum, F
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, Http404 # Added HttpResponse* imports
from .models import Product, Category, Cart, CartItem, Order, OrderItem, ProductImage, Review, Question, Customer, Promotion, ProductVariant, PromoCode, Team # Added ProductVariant, PromoCode
from .forms import SignUpForm, CustomLoginForm, CustomerProfileForm, ReviewForm, QuestionForm # Removed OrderForm as it's not defined yet
from .utils import get_cart, update_cart_totals, decrease_variant_stock, increase_variant_stock
from django.utils import timezone # For offer filtering
import uuid # For generating order ID

# Create your views here.
def index(request):
    best_selling_products = Product.objects.filter(best_selling=True).order_by('-updated_at')[:8]
    new_arrivals = Product.objects.order_by('-created_at')[:8]
    # Active promotions that haven't ended and have started
    active_promotions = Promotion.objects.filter(
        active=True, 
        start_date__lte=timezone.now(), 
        end_date__gte=timezone.now()
    ).order_by('-start_date')[:3]
    # Categories with at least one product, ordered by name or some other criteria
    top_categories = Category.objects.annotate(num_products=Count('products')).filter(num_products__gt=0).order_by('-num_products')[:6]
    teams = Team.objects.all()[:6]
    context = {
        'best_selling_products': best_selling_products,
        'new_arrival_products': new_arrivals,
        'promotions': active_promotions,
        'categories': top_categories,
        'page_title': 'Homepage', # Example for base.html title block
        'teams' : teams
    }
    return render(request, 'ecommerce/index.html', context)

def teams(request):
    teams = Team.objects.all()[:6]
    context = {
        'teams': teams
    }
    return render(request, 'ecommerce/team.html', context)

def about_us(request):
    return render(request, 'ecommerce/about.html',{})

def product_list(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category') # Assuming category is passed as slug or ID
    sort_by = request.GET.get('sort', '-created_at')

    # products = Product.objects.filter(Q(quantity__gt=0) | Q(variants__quantity__gt=0)).distinct() # Products with own stock or variant stock
    products = Product.objects.all() # Products with own stock or variant stock

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(type__icontains=query) |
            Q(category__category__icontains=query) # Assuming Category model has 'category' field for name
        )

    selected_category_name = None
    if category_slug:
        try:
            # Assuming category_slug is the name. Adjust if it's an ID or actual slug field.
            category_obj = Category.objects.get(category__iexact=category_slug.replace('-',' ')) 
            products = products.filter(category=category_obj)
            selected_category_name = category_obj.category
        except Category.DoesNotExist:
            # products = Product.objects.none() # Or raise Http404
            messages.warning(request, f"Category '{category_slug}' not found.")
            pass # Show all products or handle as desired
    
    # Sorting logic (ensure display_price is available as a property or annotation)
    # For DecimalField sorting with potential None (new_price), consider Coalesce or specific annotations if needed.
    # A simple way is to ensure display_price property works well or sort on model fields directly.
    valid_sort_options = {
        'price_asc': 'price', # Simplified: use base price. Enhance with display_price later if complex.
        'price_desc': '-price',
        'name_asc': 'name',
        'name_desc': '-name',
        'newest': '-created_at',
    }
    products = products.order_by(valid_sort_options.get(sort_by, '-created_at'))

    # all_categories = Category.objects.annotate(num_products=Count('product')).filter(num_products__gt=0).order_by('category')
    all_categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': all_categories,
        'selected_category_name': selected_category_name,
        'search_query': query,
        'current_sort': sort_by,
        'page_title': selected_category_name or 'All Products'
    }
    return render(request, 'ecommerce/categories.html', context) # Using categories.html for product listing


# Products Pages

def products_by_category(request, category_name): # category_name could be slug from URL
    category = get_object_or_404(Category, category__iexact=category_name.replace('-',' '))
    products = Product.objects.filter(category=category).filter(Q(quantity__gt=0) | Q(variants__quantity__gt=0)).distinct()
    all_categories = Category.objects.annotate(num_products=Count('product')).filter(num_products__gt=0).order_by('category')
    
    context = {
        'products': products,
        'categories': all_categories,
        'selected_category_name': category.category,
        'page_title': category.category
    }
    return render(request, 'ecommerce/categories.html', context)


def category_list(request):
    categories = Category.objects.annotate(num_products=Count('product')).filter(num_products__gt=0).order_by('category')
    context = {
        'categories': categories,
        'page_title': 'Product Categories'
    }
    return render(request, 'ecommerce/categories.html', context) # Create this template if needed

def best_selling(request):
    products = Product.objects.filter(best_selling=True).order_by('-updated_at')

    context = {
        'products': products,
        'page_title': 'Best Selling - MBA'
    }
    return render(request, 'ecommerce/categories.html', context) # Create this template if needed

from django.utils.timezone import now, timedelta
def new_arrivals(request):
    _30days = now() - timedelta(days=30)
    products = Product.objects.filter(created_at = _30days).order_by('-created_at')
    context = {
        'products': products,
        'page_title': 'New Arrivals - MBA'
    }
    return render(request, 'ecommerce/categories.html', context) 


def team(request, team_id):
    team = Team.objects.get(id = team_id)
    products = Product.objects.filter(team = team).order_by('-created_at')
    context = {
        'products': products,
        'page_title': f' {team.name} Products - MBA'
    }
    return render(request, 'ecommerce/categories.html', context) 


def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    related_products = Product.objects.filter(category=product.category).exclude(id=id)[:4]
    reviews = product.reviews.all().order_by('-created_at')
    questions = product.questions.all().order_by('-created_at')
    images = ProductImage.objects.filter(product=product)
    additional_images = product.additional_images.all()
    available_variants = product.variants.filter(quantity__gt=0).order_by('size')
    images = images if images else None
    review_form = ReviewForm()
    question_form = QuestionForm()

    context = {
        'product': product,
        'available_variants': available_variants,
        'related_products': related_products,
        'reviews': reviews,
        'questions': questions,
        'images': images,
        'additional_images': additional_images,
        'review_form': review_form,
        'question_form': question_form,
        'page_title': product.name
    }
    return render(request, 'ecommerce/product_detail.html', context)

# --- Cart Views ---
def cart_detail(request):
    cart = get_cart(request)
    context = {
        'cart': cart,
        'page_title': 'Your Shopping Cart'
    }
    return render(request, 'ecommerce/cart.html', context)

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_cart(request)
    
    variant_id = request.POST.get('variant_id') # Expecting ProductVariant ID
    quantity = int(request.POST.get('quantity', 1))

    if quantity <= 0:
        messages.error(request, "Quantity must be a positive number.")
        return redirect('ecommerce:product_detail', id=product_id)

    selected_variant = None
    if product.variants.exists(): # Product has variants
        if not variant_id:
            messages.error(request, "Please select a size/variant for this product.")
            return redirect('ecommerce:product_detail', id=product_id)
        try:
            selected_variant = ProductVariant.objects.get(id=variant_id, product=product)
            if selected_variant.quantity < quantity:
                messages.error(request, f"Not enough stock for {product.name} ({selected_variant.size}). Available: {selected_variant.quantity}")
                return redirect('ecommerce:product_detail', id=product_id)
        except ProductVariant.DoesNotExist:
            messages.error(request, "Selected variant not found.")
            return redirect('ecommerce:product_detail', id=product_id)
    else: # Product does not have variants, check main product quantity
        if product.quantity < quantity:
            messages.error(request, f"Not enough stock for {product.name}. Available: {product.quantity}")
            return redirect('ecommerce:product_detail', id=product_id)

    # Determine color (can be part of variant or main product)
    # For simplicity, using product's main color if not part of variant explicitly
    color_to_add = selected_variant.product.color if selected_variant else product.color 

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=selected_variant, # This is a ProductVariant instance or None
        color=color_to_add, # Or selected_variant.color if variants have distinct colors
        defaults={'quantity': quantity}
    )

    if not created:
        new_quantity = cart_item.quantity + quantity
        # Stock check before increasing quantity
        if selected_variant and selected_variant.quantity < new_quantity:
            messages.error(request, f"Cannot add more. Not enough stock for {product.name} ({selected_variant.size}). Available: {selected_variant.quantity}, In Cart: {cart_item.quantity}")
            return redirect('ecommerce:cart_detail')
        elif not selected_variant and product.quantity < new_quantity:
            messages.error(request, f"Cannot add more. Not enough stock for {product.name}. Available: {product.quantity}, In Cart: {cart_item.quantity}")
            return redirect('ecommerce:cart_detail')
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, f"Updated quantity for {product.name} in your cart.")
    else:
        messages.success(request, f"{product.name} ({selected_variant.size if selected_variant else 'Standard'}) added to cart.")

    update_cart_totals(cart)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': # Handle AJAX request
        return JsonResponse({'message': 'Item added/updated', 'cart_item_count': cart.number_of_items})
    return redirect('ecommerce:cart_detail')

def remove_from_cart(request, item_id):
    cart = get_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart) # Ensure item belongs to current cart
    
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f"{product_name} removed from your cart.")
    
    update_cart_totals(cart)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'message': 'Item removed', 'cart_item_count': cart.number_of_items, 'cart_total_price': cart.total_price})
    return redirect('ecommerce:cart_detail')

def update_cart_item(request, item_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests are allowed.")

    cart = get_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    
    quantity = int(request.POST.get('quantity', 0))

    if quantity <= 0:
        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f"{product_name} removed from cart.")
    else:
        # Stock check
        if cart_item.size and cart_item.size.quantity < quantity:
            messages.error(request, f"Not enough stock for {cart_item.product.name} ({cart_item.size.size}). Max: {cart_item.size.quantity}")
        elif not cart_item.size and cart_item.product.quantity < quantity:
            messages.error(request, f"Not enough stock for {cart_item.product.name}. Max: {cart_item.product.quantity}")
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, f"Updated quantity for {cart_item.product.name}.")
            
    update_cart_totals(cart)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'message': 'Cart updated', 
            'cart_item_count': cart.number_of_items,
            'item_total_price': cart_item.get_total_price() if cart_item.pk else 0, # If item still exists
            'cart_total_price': cart.total_price
        })
    return redirect('ecommerce:cart_detail')

# --- Auth Views ---
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('ecommerce:index')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend') # Specify backend
            messages.success(request, 'Account created successfully! You are now logged in.')
            return redirect('ecommerce:index')
        else:
            # Pass errors to template via messages or form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label or field}: {error}")
    else:
        form = SignUpForm()
    return render(request, 'ecommerce/signup.html', {'form': form, 'page_title': 'Create Account'})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('ecommerce:index')
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f'Welcome back, {username}!')
                next_page = request.POST.get('next') or request.GET.get('next') # Check POST then GET for next
                return redirect(next_page or 'ecommerce:index')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            # Form is not valid (e.g. fields missing)
            messages.error(request, 'Please enter both username and password.') 
    else:
        form = CustomLoginForm()
    return render(request, 'ecommerce/login.html', {'form': form, 'next': request.GET.get('next', ''), 'page_title': 'Login'})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('ecommerce:index')

# --- User Profile & Orders ---
@login_required
def profile(request):
    customer = get_object_or_404(Customer, user=request.user)
    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    form = CustomerProfileForm(instance=customer) # For display or if edit is on same page
    context = {
        'customer': customer,
        'orders': orders,
        'form': form,
        'page_title': 'My Profile'
    }
    return render(request, 'ecommerce/profile.html', context)

@login_required
def profile_edit(request):
    customer = get_object_or_404(Customer, user=request.user)
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            user = request.user
            user.first_name = form.cleaned_data.get('first_name')
            # user.last_name = form.cleaned_data.get('second_name') # Map to Customer.second_name
            user.email = form.cleaned_data.get('email')
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('ecommerce:profile')
        else:
             for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label or field}: {error}")
    else:
        form = CustomerProfileForm(instance=customer)
    # Typically, profile edit is a separate template or a modal on profile page
    return render(request, 'ecommerce/profile_edit.html', {'form': form, 'page_title': 'Edit Profile'}) 

@login_required
def checkout(request):
    cart = get_cart(request)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty. Add items to proceed to checkout.")
        return redirect('ecommerce:cart_detail')

    customer = None
    if request.user.is_authenticated:
        customer, _ = Customer.objects.get_or_create(
            user=request.user, 
            defaults={'email': request.user.email, 'first_name': request.user.first_name}
        )
    
    # Simplified OrderForm - assuming it takes POST data for shipping etc.
    # from .forms import OrderForm # You'll need to create this form
    # order_form = OrderForm(request.POST or None, initial=initial_checkout_data(customer))

    if request.method == 'POST':
        # Extract data from POST - this needs to be robust
        full_address = request.POST.get('fullAddress')
        city = request.POST.get('city')
        phone = request.POST.get('phone')
        email = request.POST.get('email') # For guests or to confirm for logged-in users
        note = request.POST.get('note')
        promo_code_str = request.POST.get('promo_code')

        # Validation (basic example, use Django forms for proper validation)
        if not all([full_address, city, phone, email]):
            messages.error(request, "Please fill in all required shipping details.")
            return render(request, 'ecommerce/checkout.html', {'cart': cart, 'page_title': 'Checkout'}) # Re-render with error

        # Create Order
        order_total_price = cart.total_price # Start with cart total
        applied_promo = None
        if promo_code_str:
            try:
                promo = PromoCode.objects.get(code=promo_code_str)
                if promo.is_valid():
                    discount_amount = (promo.discount / 100) * order_total_price
                    order_total_price -= discount_amount
                    applied_promo = promo
                    messages.success(request, f"Promo code '{promo.code}' applied!")
                else:
                    messages.error(request, f"Promo code '{promo.code}' is invalid or expired.")
            except PromoCode.DoesNotExist:
                messages.error(request, "Invalid promo code.")

        current_customer = customer
        if not request.user.is_authenticated:
            # For guests, you might create a temporary customer or store details directly on Order
            # Here, we attempt to find/create a customer by email for guests (optional)
            current_customer, _ = Customer.objects.get_or_create(
                email=email, 
                defaults={'first_name': request.POST.get('first_name', ''), 'phone': phone}
            )

        order = Order.objects.create(
            customer=current_customer if request.user.is_authenticated else None, # Link to customer if logged in
            order_id=f"MBA-{str(uuid.uuid4())[:8].upper()}",
            promo_code=applied_promo,
            total_price=order_total_price,
            fullAddress=full_address,
            city=city,
            phone=phone,
            email=email, # Store email for guest orders too
            note=note,
            status='pending' # Or 'paid' if payment is integrated and successful
        )

        # Create OrderItems and decrease stock
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                size=item.size.size if item.size else None, # Store size string
                color=item.color,
                price=item.product.display_price # Price at time of order
            )
            # Decrease stock
            if item.size: # ProductVariant
                if not decrease_variant_stock(item.size.id, item.quantity):
                    messages.error(request, f"Critical: Stock issue for {item.product.name} ({item.size.size}). Order processing halted. Contact support.")
                    order.status = 'failed' # Mark order as failed due to stock issue
                    order.save()
                    # TODO: Rollback or compensation logic might be needed here
                    return redirect('ecommerce:checkout') # Or an error page
            else: # Main product stock
                if product.quantity < item.quantity:
                     messages.error(request, f"Critical: Stock issue for {item.product.name}. Order processing halted. Contact support.")
                     order.status = 'failed'
                     order.save()
                     return redirect('ecommerce:checkout')
                item.product.quantity = F('quantity') - item.quantity
                item.product.save()
        
        if applied_promo:
            applied_promo.used_count = F('used_count') + 1
            applied_promo.save()

        # Clear the cart (or mark as completed)
        cart.items.all().delete() # Deletes cart items
        update_cart_totals(cart) # Resets cart totals
        # Optionally, delete the cart itself for guest users or mark as inactive for registered users
        # if not request.user.is_authenticated and request.session.get('cart_id'):
        #     Cart.objects.filter(device_token=request.session['cart_id']).delete()
        #     del request.session['cart_id']

        messages.success(request, f"Order #{order.order_id} placed successfully! Thank you for your purchase.")
        return redirect('ecommerce:order_detail', order_id=order.id)
    
    else: # GET request
        initial_checkout_data = {}
        if customer:
            initial_checkout_data = {
                'email': customer.email or (request.user.email if request.user.is_authenticated else ''),
                'phone': customer.phone,
                'fullAddress': customer.fullAddress,
                'city': customer.city,
                'first_name': customer.first_name or (request.user.first_name if request.user.is_authenticated else ''),
                'second_name': customer.second_name
            }
        # else for guest users, form will be empty

    context = {
        'cart': cart,
        'page_title': 'Checkout',
        'initial_data': initial_checkout_data # Pass to prefill form if using Django forms
    }
    return render(request, 'ecommerce/checkout.html', context)

@login_required
def order_history(request):
    # Customer might not exist if user signed up but never made a purchase or filled profile
    customer = Customer.objects.filter(user=request.user).first()
    orders = []
    if customer:
        orders = Order.objects.filter(Q(customer=customer) | Q(email=request.user.email)).order_by('-created_at')
    elif request.user.email: # Fallback for users who might have guest orders with their email
        orders = Order.objects.filter(email=request.user.email).order_by('-created_at')
        if not orders.exists() and not customer:
             messages.info(request, "You have no order history. Your past guest orders (if any) might not be linked if placed with a different email.")

    context = {
        'orders': orders,
        'page_title': 'My Orders'
    }
    return render(request, 'ecommerce/order_history.html', context)

@login_required
def order_detail(request, order_id):
    try:
        # Allow access if order is linked to the user's customer profile OR order email matches user's email
        order = Order.objects.get(id=order_id)
        is_owner = (order.customer and order.customer.user == request.user) or (order.email == request.user.email)
        
        if not is_owner and not request.user.is_staff:
            messages.error(request, "You do not have permission to view this order.")
            return redirect('ecommerce:order_history')
    except Order.DoesNotExist:
        raise Http404("Order not found.")
        
    context = {
        'order': order,
        'page_title': f'Order #{order.order_id}'
    }
    return render(request, 'ecommerce/order_detail.html', context)

# --- Reviews and Questions ---
@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Check if user has purchased this product (optional but good practice)
    # has_purchased = OrderItem.objects.filter(order__customer__user=request.user, product=product, order__status='delivered').exists()
    # if not has_purchased:
    #     messages.error(request, "You can only review products you have purchased and received.")
    #     return redirect('ecommerce:product_detail', id=product_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            # Optional: Check if user already reviewed
            # existing_review = Review.objects.filter(product=product, user=request.user).exists()
            # if existing_review:
            # messages.error(request, "You've already reviewed this product.")
            # return redirect('ecommerce:product_detail', id=product_id)

            review = form.save(commit=False)
            review.product = product
            # review.user = request.user # Add user FK to Review model if desired
            review.save()
            messages.success(request, 'Thank you! Your review has been submitted.')
            return redirect('ecommerce:product_detail', id=product_id)
        else:
            messages.error(request, 'There was an error with your review. Please check the details.')
    else: # Should not happen if form is on product page and submitted via POST
        form = ReviewForm()

    # If form invalid, re-render product page with errors
    # This requires product_detail to handle forms passed in context for errors
    context = product_detail_context_data(product, review_form=form) # Helper function for context
    return render(request, 'ecommerce/product.html', context)

@login_required
def add_question(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.product = product
            # question.user = request.user # Add user FK if desired
            question.save()
            messages.success(request, 'Your question has been submitted. We will answer it shortly.')
            return redirect('ecommerce:product_detail', id=product_id)
        else:
            messages.error(request, 'There was an error submitting your question.')
    else:
        form = QuestionForm()
    
    context = product_detail_context_data(product, question_form=form)
    return render(request, 'ecommerce/product.html', context)

# Helper for product_detail context to avoid repetition in add_review/add_question error paths
def product_detail_context_data(product, review_form=None, question_form=None):
    return {
        'product': product,
        'available_variants': product.variants.filter(quantity__gt=0).order_by('size'),
        'related_products': Product.objects.filter(category=product.category).exclude(id=product.id)[:4],
        'reviews': product.reviews.all().order_by('-created_at'),
        'questions': product.questions.all().order_by('-created_at'),
        'videos': product.videos.all(),
        'additional_images': product.additional_images.all(),
        'review_form': review_form or ReviewForm(),
        'question_form': question_form or QuestionForm(),
        'page_title': product.name
    }

# Placeholder views for static pages if needed from base.html links
def privacy_policy_view(request):
    # return render(request, 'ecommerce/privacy_policy.html', {'page_title': 'Privacy Policy'})
    messages.info(request, "Privacy Policy page is not yet implemented.")
    return redirect('ecommerce:index')

def terms_conditions_view(request):
    # return render(request, 'ecommerce/terms_conditions.html', {'page_title': 'Terms & Conditions'})
    messages.info(request, "Terms & Conditions page is not yet implemented.")
    return redirect('ecommerce:index')

#Make sure every thing is work and competable with the frontend that you will take and copy from frontend/ecommerce after you done the ecommerce should be done and wokring well
