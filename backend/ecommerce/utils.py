from .models import Cart, CartItem, ProductVariant
from django.shortcuts import get_object_or_404

def get_cart(request):
    """Retrieve or create a cart for the current session/user."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        # If an authenticated user had a session cart, merge it or handle as needed
        session_cart_id = request.session.get('cart_id')
        if session_cart_id:
            try:
                guest_cart = Cart.objects.get(device_token=session_cart_id, user__isnull=True)
                # Merge guest_cart items into user_cart
                for item in guest_cart.items.all():
                    # Check if item already exists in user cart (product, size, color)
                    existing_item, item_created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=item.product,
                        size=item.size, # This is ProductVariant instance
                        color=item.color, 
                        defaults={'quantity': item.quantity}
                    )
                    if not item_created:
                        existing_item.quantity += item.quantity
                        existing_item.save()
                    item.delete() # Remove item from guest cart or delete guest cart
                guest_cart.delete() # Delete the guest cart after merging
                del request.session['cart_id']
            except Cart.DoesNotExist:
                pass # No guest cart to merge
    else:
        device_token = request.session.get('cart_id')
        if not device_token:
            # Generate a unique device token if one doesn't exist
            # This could be more robust, e.g., using uuid
            import uuid
            device_token = str(uuid.uuid4())
            request.session['cart_id'] = device_token
        
        cart, created = Cart.objects.get_or_create(device_token=device_token, user__isnull=True)
    
    # Recalculate cart totals
    update_cart_totals(cart)
    return cart

def update_cart_totals(cart):
    """Recalculate total_price and number_of_items for a cart."""
    total_price = 0
    number_of_items = 0
    for item in cart.items.all():
        total_price += item.get_total_price()
        number_of_items += item.quantity
    cart.total_price = total_price
    cart.number_of_items = number_of_items
    cart.save()

# It might be useful to have a context processor to make the cart available in all templates
def cart_context_processor(request):
    cart = get_cart(request)
    return {
        'current_cart': cart,
        'cart_item_count': cart.number_of_items if cart else 0
    }


# Helper to manage product variant stock during cart/order operations
def decrease_variant_stock(variant_id, quantity_to_decrease):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    if variant.quantity >= quantity_to_decrease:
        variant.quantity -= quantity_to_decrease
        variant.save()
        return True
    return False # Not enough stock

def increase_variant_stock(variant_id, quantity_to_increase):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.quantity += quantity_to_increase
    variant.save() 