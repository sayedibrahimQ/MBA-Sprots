from django.shortcuts import render

from datetime import timezone
import json
from django.contrib import messages
import uuid
from .utils import send_facebook_add_to_cart_event, send_facebook_purchase_event, send_facebook_view_content_event
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from .models import DeliveryFees, Images, Order, OrderItem, Product, Question, Review, Size, Video
from django.core.paginator import Paginator
from .models import Cart, CartItem, Product, PromoCode, Customer
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from django.views.decorators.csrf import csrf_exempt
from .models import Emails
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test


def admin_required(view_func):
    decorated_view_func = login_required(
        user_passes_test(lambda u: u.is_staff, login_url='/admin/login/')(view_func),
        login_url='/admin/login/'
    )
    return decorated_view_func

def products(request):
    products = Product.objects.all()
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_object = paginator.get_page(page_number)
    return render(request, 'products.html', {'prods' : page_object})

def productsClothes(request):
    products = Product.objects.filter(category = 'Clothes')
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_object = paginator.get_page(page_number)
    return render(request, 'products.html', {'prods' : page_object})

def productsCareProducts(request):
    products = Product.objects.filter(category = 'CareProducts')
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_object = paginator.get_page(page_number)
    return render(request, 'products.html', {'prods' : page_object})

def productsAccessories(request):
    products = Product.objects.filter(category = 'Accessories')
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_object = paginator.get_page(page_number)
    return render(request, 'products.html', {'prods' : page_object})

def product(request, pid):
    product = Product.objects.get(id=pid)
    send_facebook_view_content_event(request, product)
    qs = Question.objects.filter(product=product)
    related_products = Product.objects.filter(type=product.type)
    reviews = Review.objects.filter(product= product)
    videos = Video.objects.filter(product= product)
    sizes = Size.objects.filter(product = product)
    colors = product.color.split(',')
    images = Images.objects.filter(product=product)
    return render(request,
                  'single-product.html',
                  {'product': product,
                   'products': related_products,
                   'questions' : qs,
                   'reviews' : reviews,
                   'videos' : videos,
                   'images' : images,
                   'sizes' : sizes, 
                   'colors': colors
                   })

def cart_view(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
    else:
        device_token = request.COOKIES.get('device')
        cart, created = Cart.objects.get_or_create(device_token = device_token)
        cart_items = CartItem.objects.filter(cart=cart)

    subtotal = sum((item.product.new_price if item.product.discount else item.product.price) * item.quantity for item in cart_items)
    total = subtotal  # Add any additional fees or discounts here

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total': total,
    }
    return render(request, 'cart.html', context)


def add_to_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        size_id = request.POST.get('size_id')
        color = request.POST.get('color')
        product = get_object_or_404(Product, id=product_id)

        # Check if the product's quantity is zero
        if product.quantity == 0:
            return JsonResponse({'status': 'out_of_stock', 'message': 'This product is out of stock!'})

        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            device_token = request.COOKIES.get('device')
            cart, created = Cart.objects.get_or_create(device_token=device_token)

        cart.number_of_items += 1

        # Get or create the CartItem with the specific size
        size = None
        if size_id:
            size = get_object_or_404(Size, id=size_id)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, size=size, color = color if color else 'None'
        )
        cart_item.color = color if color else 'None'

        if not created:
            # Check if there's enough stock to increase the quantity (you might need to adjust this if stock depends on size)
            if cart_item.quantity < product.quantity:
                cart_item.quantity += 1
            else:
                return JsonResponse({'status': 'out_of_stock', 'message': 'Not enough stock available to add more items.'})

        send_facebook_add_to_cart_event(request, product)
        cart_item.save()
        # Calculate new cart item count
        total_items = CartItem.objects.filter(cart=cart).aggregate(total_items=Sum('quantity'))['total_items']

        return JsonResponse({'status': 'success', 'cart_item_count': total_items})

    return JsonResponse({'status': 'error'}, status=400)

def get_product_sizes(request):
    product_id = request.GET.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    sizes = Size.objects.filter(product = product)
    size_list = []
    for size in sizes:
        size_list.append({'id': size.id, 'name': size.size})
    print(size_list)
    return JsonResponse({'status': 'success', 'sizes': size_list})

def remove_from_cart(request, cart_item_id):
    # Get the cart item based on its ID
    cart_item = get_object_or_404(CartItem, id=cart_item_id)

    if cart_item.quantity > 1:
        # If the quantity is greater than 1, decrease the quantity by 1
        cart_item.quantity -= 1
        cart_item.save()
    else:
        # If the quantity is 1, delete the item from the cart
        cart_item.delete()

    # Redirect back to the cart detail page
    return redirect('store:cart_view')

def get_delivery_fee(request):
    city = request.GET.get('city')  # Get city from the AJAX request
    if city:
        try:
            delivery_fee = DeliveryFees.objects.get(city=city).delivery_fee
            return JsonResponse({'delivery_fee': delivery_fee})
        except DeliveryFees.DoesNotExist:
            return JsonResponse({'error': 'City not found'}, status=404)
    return JsonResponse({'error': 'City not provided'}, status=400)

@csrf_exempt 
def apply_promo_code(request):
    if request.method == 'POST':
        promo_code = request.POST.get('promo_code')
        cart_total = request.POST.get('cart_total')

        if request.user.is_authenticated:
            customer, created = Customer.objects.get_or_create(user=request.user)
            cart = Cart.objects.get(user=request.user)
        else:
            device_token = request.COOKIES.get('device')
            customer, created = Customer.objects.get_or_create(device_token=device_token)
            cart = Cart.objects.get(device_token=device_token)
        try:
            # Convert cart_total to Decimal
            cart_total = Decimal(cart_total)  # Ensure it is a Decimal for accurate calculations
        except (ValueError, InvalidOperation):
            return JsonResponse({'status': 'error', 'message': 'Invalid cart total.'})

        try:
            promo = PromoCode.objects.get(code=promo_code)
            if promo.is_valid():
                discount_amount = (promo.discount / 100) * cart_total  # Now this should work
                new_total = cart_total - discount_amount
                request.session['discount'] = promo.code  # Store discount in session
                promo.used_count += 1
                promo.save()
                cart.total_price = new_total
                cart.save()
                return JsonResponse({'status': 'success', 'new_total': new_total, 'message': 'Promo code applied successfully!'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Promo code is invalid or expired.'})
        except PromoCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Promo code does not exist.'})

    return JsonResponse({'status': 'error'}, status=400)

def checkout(request):
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(user=request.user)
    else:
        device_token = request.COOKIES.get('device')
        customer, created = Customer.objects.get_or_create(device_token=device_token)

    # Retrieve cart and cart items
    if request.user.is_authenticated:
        cart = Cart.objects.get(user=request.user)
    else:
        cart = Cart.objects.get(device_token=device_token)

    cart_items = CartItem.objects.filter(cart=cart)

    # Calculate total price
    total_price_without_discount = sum(Decimal(item.get_total_price()) for item in cart_items)
    promoCode = request.session.get('discount')
    promo = 'null'
    if promoCode:
        promo = PromoCode.objects.get(code=promoCode)
        
    # Get delivery city from cookie
    pa = request.COOKIES.get('promo')
    if pa == 'true':
        total_price = cart.total_price
    else:
        total_price = sum(item.get_total_price() for item in cart_items)
        cart.total_price = total_price
        cart.save()

    if request.method == 'POST':
        # Collect customer data for billing information
        first_name = request.POST['first_name']
        second_name = request.POST['second_name']
        city = request.POST['city']
        address = request.POST['Address']
        phone = request.POST['phone1']
        second_phone = request.POST['phone2']
        email = request.POST['email']

        # Update customer information
        customer.first_name = first_name
        customer.second_name = second_name
        customer.phone = phone
        customer.phone2 = second_phone
        customer.fullAddress = address
        customer.city = city
        customer.email = email
        customer.save()

        total_price = Decimal(request.POST['total_price'])
        
        # Create order
        try:
            
            order = Order.objects.create(
                customer=customer,
                total_price=total_price,
                order_id=str(uuid.uuid3(int,int)),
                promo_code=promo,
                phone = phone,
                email = email,
                fullAddress=address,
                city=city,
                note='',
                status='processing',
            )
        except:
            order = Order.objects.create(
                customer=customer,
                total_price=total_price,
                order_id=str(uuid.uuid4()),
                phone = phone,
                email = email,
                fullAddress=address,
                city=city,
                note='',
                status='processing',
            )
            
        # Save each order item
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                size = item.size,
                color = item.color if item.color else 'None',
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,  # Storing product price at time of purchase
            )

        return redirect('store:ordered', order_id=order.id)
    
    discount_am = total_price_without_discount - total_price
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_without_discount': total_price_without_discount,
        'discount': discount_am,
        'customer': customer,
    })

def checkout_single_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    error_message = None
    final_price = product.new_price if product.discount else product.price
    sizes = Size.objects.filter(product = product)
    colors = product.color.split(',')
    if request.method == 'POST':
        # Collect data from the form
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        color = request.POST.get('selected_color')
        size = request.POST.get('size')
        note = request.POST.get('note')
        promo = None
        promo_code_input = request.POST.get('promo_code')
        if colors:
            if not color:
                error_message = 'Please select a color.'
        if sizes:
            if not size:
                error_message = 'Please select a size.'
        # Validate and apply promo code (optional)
        if promo_code_input:
            try:
                promo = PromoCode.objects.get(code=promo_code_input, active=True)
                if not promo.is_valid():
                    error_message = 'Promo code has expired.'
                else:
                    discount_amount = final_price * (promo.discount / 100)
                    final_price -= discount_amount
            except PromoCode.DoesNotExist:
                error_message = 'Invalid promo code.'

        if not error_message:
            if request.user.is_authenticated:
                customer, created = Customer.objects.get_or_create(user=request.user)
            else:
                device_token = request.COOKIES.get('device')
                customer, created = Customer.objects.get_or_create(device_token=device_token)
            # Update customer information
            customer.first_name = (name.split(' '))[0]
            customer.second_name = (name.split(' '))[1]
            customer.phone = phone
            customer.phone2 = ' '
            customer.fullAddress = address
            customer.city = city
            customer.email = email
            customer.save()


            # Save order details
            order = Order.objects.create(
            customer = customer,
            promo_code=promo,
            total_price =final_price,
            fullAddress = address,
            city = city,
            email=email,
            phone=phone,
            note = note
            )
            orderItem = OrderItem.objects.create(
                product=product,
                order = order,
                quantity = 1,
                price = product.new_price if product.discount else product.price,
                color = color,
                size = size if sizes else None
            )
            messages.success(request, 'Your order has been placed successfully!')
            return redirect('store:ordered', order_id=order.id)
        else:
            messages.error(request, error_message)

    context = {
        'product': product,
        'final_price': final_price,
        'sizes' : sizes,
        'colors' : colors,
    }
    return render(request, 'checkout_single_product.html', context)


def ordered(request, order_id):
    order = Order.objects.get(id=order_id)

    # Update order status to 'paid'
    # order.status = 'processing'
    order.status = 'processing'
    order.save()
    send_facebook_purchase_event(request, order)
    # Update product quantity for each item in the order
    order_items = OrderItem.objects.filter(order=order)
    subject = "Order Confirmed - DirectFashionEG"
    message = f"Thank you for your purchase { order.customer.first_name }! \n Your order is being processed and should arrive at your destination within 2-3 Days.\n TOTAL: {order.total_price} EGP \n Thank you again for your purchase. We would love to hear from you once you receive your items. \n Kind Regards, \n The DirectFashionEG"
   
    # send_order_confirmation_email(order)
                
    for item in order_items:
        product = item.product
        product.quantity -= item.quantity  # Decrease product stock
        # product.orderd += item.quantity  
        product.save()
    # Retrieve cart and cart items
    if request.user.is_authenticated:
        cart = Cart.objects.get(user=request.user)
    else:
        device_token = request.COOKIES.get('device')
        cart = Cart.objects.get(device_token=device_token)
    cart_items = CartItem.objects.filter(cart=cart)
    cart_items.delete()
    send_order_confirmation_email(order)
    return render(request, 'ordered.html', {
        'order_items' : order_items,
        'order' : order,
        
    })

def savemail(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name')
        Emails.objects.create(name = name, email = email)    
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)

def get_delivery_fee(request):
    city = request.GET.get('city')  # Get city from the AJAX request
    if city:
        try:
            delivery_fee = DeliveryFees.objects.get(city=city).delivery_fee
            return JsonResponse({'delivery_fee': delivery_fee})
        except DeliveryFees.DoesNotExist:
            return JsonResponse({'error': 'City not found'}, status=404)
    return JsonResponse({'error': 'City not provided'}, status=400)

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_order_confirmation_email(order):
    customer_email = order.customer.email
    subject = f"Order Confirmation - #{order.id}"
    adminSubject = f"Order - #{order.id}"
    from_email = 'contact@egpolka.store'
    admin_email = 'contact@sayedibrahim.co'
    # Render the HTML template and strip to plain text as fallback
    html_content = render_to_string('order_confirmation.html', {
        'customer_name': order.customer.first_name,
        'order_id': order.id,
        'order_date': order.created_at,
        'order_items': order.order_items.all(),  # Assuming related name is order_items
        'order_total': order.total_price,
    })
    
    admin_html_content = render_to_string('admin_order_confirmation.html', {
        'customer_name': order.customer.first_name,
        'order_id': order.id,
        'order_date': order.created_at,
        'order_items': order.order_items.all(),  # Assuming related name is order_items
        'order_total': order.total_price,
        'order' : order,
    })
    
    text_content = strip_tags(html_content)
    admin_text_content = strip_tags(admin_html_content)

    # Send email
    email = EmailMultiAlternatives(subject, text_content, from_email, [customer_email])
    adminEmail = EmailMultiAlternatives(adminSubject, admin_text_content, from_email, [admin_email])
    email.attach_alternative(html_content, "text/html")
    adminEmail.attach_alternative(admin_html_content, "text/html")
    email.send()
    adminEmail.send()


from django.http import JsonResponse

@login_required
@admin_required
def update_order_status(request):
    # Parse JSON data from the request body
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('new_status')
        print(order_id)
        print(new_status)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'})

    # Validate new_status
    valid_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
    print(valid_statuses)
    if new_status not in valid_statuses:
        print("Vaaallllllid")
        return JsonResponse({'success': False, 'error': 'Invalid status value.'})

    # Get the order
    order = get_object_or_404(Order, id=order_id)
    print(order.status)
    # Update the status
    order.status = new_status
    order.save()

    return JsonResponse({'success': True})

from .forms import ImageForm, ProductForm, ImageFormset, SizeForm, SizeFormset
from .models import Product
from django.contrib import messages
from django.db import transaction

def add_product(request):
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        if product_form.is_valid():
            try:
                with transaction.atomic():
                    product = product_form.save()

                    # image_formset = ImageFormset(request.POST, request.FILES, instance=product, prefix='images')
                    size_formset = SizeFormset(request.POST, instance=product, prefix='sizes')

                    # if image_formset.is_valid() and size_formset.is_valid():
                    #     # image_formset.save()
                    #     size_formset.save()
                    # else:
                    #     raise ValueError('Formsets are invalid')
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
                # Re-initialize formsets without saving
                # image_formset = ImageFormset(request.POST, request.FILES, prefix='images')
                size_formset = SizeFormset(request.POST, prefix='sizes')
                product_form = ProductForm(request.POST, request.FILES)  # Re-initialize form with POST data
                context = {
                    'product_form': product_form,
                    # 'image_formset': image_formset,
                    'size_formset': size_formset,
                }
                return render(request, 'admin/add_product.html', context)
            else:
                messages.success(request, 'Product added successfully.')
                return redirect('store:product_list')
        else:
            messages.error(request, 'Please correct the errors in the product form.')
            # image_formset = ImageFormset(request.POST, request.FILES, prefix='images')
            size_formset = SizeFormset(request.POST, prefix='sizes')
    else:
        # GET request
        product_form = ProductForm()
        # image_formset = ImageFormset(prefix='images')
        size_formset = SizeFormset(prefix='sizes')

    context = {
        'product_form': product_form,
        # 'image_formset': image_formset,
        'size_formset': size_formset,
    }
    return render(request, 'admin/add_product.html', context)

@admin_required
def edit_product(request, pk):
    product = Product.objects.get(pk=pk)
    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        # image_formset = ImageFormset(request.POST, request.FILES, instance=product)
        size_formset = SizeFormset(request.POST, instance=product)

        if product_form.is_valid() and size_formset.is_valid():
            product = product_form.save()
            # image_formset.instance = product
            # image_formset.save()
            size_formset.instance = product
            size_formset.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('store:product_list')
    else:
        product_form = ProductForm(instance=product)
        # image_formset = ImageFormset(instance=product)
        size_formset = SizeFormset(instance=product)

    context = {
        'product_form': product_form,
        # 'image_formset': image_formset,
        'size_formset': size_formset,
        'product': product,
    }
    return render(request, 'admin/edit_product.html', context)

@admin_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'admin/product_list.html', {'products': products})

@csrf_exempt
@admin_required
def remove_product_ajax(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        print(product_id)
        try:
            product = Product.objects.get(id=product_id)
            product.delete()
            return JsonResponse({'status': 'success'})
        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product not found.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@admin_required
def orders(request):
    orders_queryset = Order.objects.all()

    # Serialize orders data
    orders_data = []
    for order in orders_queryset:
        orders_data.append({
            'id': order.id,
            'name' : f'{order.customer.first_name} {order.customer.second_name}',
            'phone' : order.phone,
            'created_at': order.created_at.isoformat(),
            'total_price': str(order.total_price),  # Convert Decimal to string
            'status': order.status,
        })

    orders_json = json.dumps(orders_data)

    # Pass orders_json to the template context
    return render(request, 'admin/orders.html', {'orders_json': orders_json})


@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    customer = order.customer
    order_items = OrderItem.objects.filter(order = order)

    context = {
        'order': order,
        'customer': customer,
        'order_items': order_items,
    }
    return render(request, 'admin/order_details.html', context) 

@admin_required
def remove_item(request):
    if request.method == 'POST':
        item_id = request.POST.get('id')
        item_type = request.POST.get('type')

        if item_type == 'size':
            try:
                size = Size.objects.get(pk=item_id)
                size.delete()
                return JsonResponse({'success': True})
            except Size.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Size not found.'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid item type.'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
