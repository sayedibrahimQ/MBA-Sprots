from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from PIL import Image
from PIL import ImageFilter
import os
from django.core.validators import MinValueValidator, MaxValueValidator
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone

class ProductVariant(models.Model):
    product = models.ForeignKey('Product', related_name='variants', on_delete=models.CASCADE)
    size = models.CharField(_("Size"), max_length=100, help_text=_("e.g., S, M, L, XL, 32, 40, etc."))
    quantity = models.PositiveIntegerField(_("Stock Quantity"), default=0)
    additional_price = models.DecimalField(_("Additional Price"), max_digits=10, decimal_places=2, default=0, help_text=_("Price difference for this variant, e.g., +5.00 for XXL"))

    class Meta:
        unique_together = ('product', 'size')
        verbose_name = _("Product Variant")
        verbose_name_plural = _("Product Variants")
        ordering = ['size']

    def __str__(self):
        return f'{self.product.name} - {self.size} (Qty: {self.quantity})'

    @property
    def get_price(self):
        return self.product.display_price + self.additional_price

class Team(models.Model):
    name = models.CharField(max_length=50, blank=True, null=True)
    img = models.ImageField(upload_to='teams', default= 'teams/default.png')
    def __str__(self):
        return self.name
    

class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey('Category', related_name='products', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    product_type = models.ForeignKey('ProductType', related_name='products', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Type"), db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_active = models.BooleanField(_("Discount Active"), default=False, help_text=_("Is there an active discount?"))
    new_price = models.DecimalField(_("Discounted Price"), max_digits=10, decimal_places=2, null=True, blank=True, help_text=_("Price after discount, if applicable."))
    color_options = models.CharField(_("Color Options (comma-separated)"), max_length=255, blank=True, help_text=_("Available colors for the product if variants are not used for color."))
    description = models.TextField()
    img = models.ImageField(_("Main Image"), upload_to='products/', help_text=_("Main product image, will be compressed to WEBP."))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    best_selling = models.BooleanField(default=False, null=True, blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True, help_text=_("Is the product available for sale?"))
    team = models.ForeignKey(Team, related_name='Team',blank = True, null = True , on_delete=models.CASCADE)
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    @property
    def display_price(self):
        if self.discount_active and self.new_price is not None:
            return self.new_price
        return self.price

    def _compress_single_image(self, image_field):
        if image_field and hasattr(image_field, 'file') and image_field.file:
            try:
                if not image_field.name.lower().endswith('.webp'):
                    img_pil = Image.open(image_field)
                    output_io_stream = BytesIO()
                    img_pil = img_pil.convert('RGB')
                    
                    max_size = (1024, 1024)
                    img_pil.thumbnail(max_size, Image.Resampling.LANCZOS)

                    img_pil.save(output_io_stream, format='WEBP', quality=80)
                    output_io_stream.seek(0)
                    
                    original_name, original_ext = os.path.splitext(image_field.name)
                    new_name = original_name + '.webp'
                    
                    image_field.save(new_name, ContentFile(output_io_stream.read()), save=False)
                return True
            except Exception as e:
                print(f"Error compressing image {image_field.name if image_field else 'N/A'}: {e}")
                return False
        return None

    def save(self, *args, **kwargs):
        self._compress_single_image(self.img)
        
        if self.new_price is not None and self.new_price < self.price:
            self.discount_active = True
        else:
            self.discount_active = False
            self.new_price = None

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.name}'

class Category(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name

class ProductType(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    class Meta:
        verbose_name = _("Product Type")
        verbose_name_plural = _("Product Types")

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='additional_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/', help_text=_("Additional product image, will be compressed to WEBP."))
    alt_text = models.CharField(max_length=255, blank=True, null=True, help_text=_("Description of the image for accessibility."))

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")

    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image, 'file') and self.image.file:
            try:
                if not self.image.name.lower().endswith('.webp'):
                    img_pil = Image.open(self.image)
                    output_io_stream = BytesIO()
                    img_pil = img_pil.convert('RGB')
                    max_size = (1024, 1024)
                    img_pil.thumbnail(max_size, Image.Resampling.LANCZOS)
                    img_pil.save(output_io_stream, format='WEBP', quality=80)
                    output_io_stream.seek(0)
                    original_name, original_ext = os.path.splitext(self.image.name)
                    new_name = original_name + '.webp'
                    self.image.save(new_name, ContentFile(output_io_stream.read()), save=False)
            except Exception as e:
                print(f"Error compressing additional image {self.image.name}: {e}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name} ({self.alt_text or 'No alt text'})"

class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='customer_profile')
    device_token = models.CharField(max_length=300, blank=True, null=True, db_index=True, unique=True, help_text=_("For guest users/devices to track carts etc."))
    
    first_name = models.CharField(_("First Name"), max_length=200, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=200, blank=True)
    phone = models.CharField(_("Primary Phone"), max_length=20, blank=True)
    phone2 = models.CharField(_("Secondary Phone"), max_length=20, blank=True)
    full_address = models.CharField(_("Full Address"), max_length=500, blank=True)
    city = models.CharField(_("City"), max_length=200, blank=True)
    email = models.EmailField(_("Email"), max_length=254, db_index=True, blank=True, null=True, help_text=_("Required if user is not set (guest checkout)"))
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    def __str__(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return f"{self.first_name or ''} {self.last_name or ''} ({self.email or 'Guest'})".strip() or f"Device: {self.device_token}"

    def clean(self):
        if not self.user and not self.email:
            raise ValidationError(_("Guest customer must have an email address."))
        if self.user and self.email and self.user.email != self.email:
            pass 

    def save(self, *args, **kwargs):
        if self.user:
            if not self.first_name and self.user.first_name:
                self.first_name = self.user.first_name
            if not self.last_name and self.user.last_name:
                self.last_name = self.user.last_name
            if not self.email and self.user.email:
                self.email = self.user.email
        super().save(*args, **kwargs)

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, related_name='reviews', on_delete=models.CASCADE, null=True, blank=True, help_text=_("Customer who wrote the review. Can be null for anonymous."))
    user_name = models.CharField(_("Display Name"), max_length=100, blank=True, help_text=_("Name to display if customer is anonymous or wants a different name."))
    review_text = models.TextField(_("Review Text"))
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_approved = models.BooleanField(_("Approved"), default=True, help_text=_("Is the review approved to be shown?"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")

    def __str__(self):
        display_name = self.user_name or (self.customer.get_full_name() if self.customer else _("Anonymous"))
        return f"Review for {self.product.name} by {display_name} - Rating: {self.rating}"
        

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    device_token = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    number_of_items = models.PositiveIntegerField(default=0)
    promo_code = models.ForeignKey('PromoCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='carts')

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")
        constraints = [
            models.CheckConstraint(
                check=(models.Q(user__isnull=False) & models.Q(device_token__isnull=True)) | 
                      (models.Q(user__isnull=True) & models.Q(device_token__isnull=False)),
                name='cart_user_or_device_token_exclusive',
                violation_error_message=_("Cart must be associated with a user or a device token, but not both or neither.")
            )
        ]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username} (ID: {self.id})"
        elif self.device_token:
            return f"Guest Cart (Device: {self.device_token}, ID: {self.id})"
        return f"Cart ID: {self.id} (Unassociated)"

    def get_subtotal(self):
        return sum(item.get_total_price() for item in self.items.all())

    def get_discount_amount(self):
        if self.promo_code and self.promo_code.is_valid():
            subtotal = self.get_subtotal()
            return (subtotal * self.promo_code.discount_percentage) / 100
        return 0

    def calculate_total_price(self):
        subtotal = self.get_subtotal()
        discount = self.get_discount_amount()
        return subtotal - discount

    def update_cart_values(self, save=True):
        self.number_of_items = self.items.aggregate(total_items=models.Sum('quantity'))['total_items'] or 0
        self.total_price = self.calculate_total_price()
        if save:
            self.save(update_fields=['number_of_items', 'total_price', 'updated_at'])

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, help_text=_("Select product variant (e.g. size) if applicable"))
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product', 'variant')
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")
        ordering = ['-added_at']

    def get_price_at_addition(self):
        if self.variant:
            return self.variant.get_price
        return self.product.display_price
            
    def get_total_price(self):
        return self.get_price_at_addition() * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.variant.size if self.variant else 'Standard'}) in cart {self.cart.id}"

    def clean(self):
        super().clean()
        if self.variant and self.variant.product != self.product:
            raise ValidationError(_("The selected variant does not belong to the selected product."))
        if self.quantity <= 0:
            raise ValidationError(_("Quantity must be at least 1."))
        stock_available = self.variant.quantity if self.variant else self.product.is_active
        if self.variant and self.quantity > self.variant.quantity:
            raise ValidationError(_(f"Not enough stock for {self.product.name} ({self.variant.size}). Available: {self.variant.quantity}"))
        elif not self.variant and not self.product.is_active:
             raise ValidationError(_(f"Product {self.product.name} is not available."))

class DeliveryFees(models.Model):
    city = models.CharField(_("City/Region"), max_length=255, db_index=True, unique=True)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = _("Delivery Fee")
        verbose_name_plural = _("Delivery Fees")
        ordering = ['city']

    def __str__(self):
        return f"{self.city}: {self.delivery_fee} EGP"

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    discount_percentage = models.DecimalField(_("Discount Percentage"), max_digits=5, decimal_places=2, help_text=_("Percentage discount (e.g., 10 for 10%)"))
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    max_usage_limit = models.PositiveIntegerField(_("Maximum Usage Limit"), default=1, help_text=_("Max number of times this promo code can be used in total."))
    used_count = models.PositiveIntegerField(default=0, editable=False)
    min_cart_value = models.DecimalField(_("Minimum Cart Value"), max_digits=10, decimal_places=2, null=True, blank=True, help_text=_("Minimum cart total for the promo to be applicable."))

    class Meta:
        verbose_name = _("Promo Code")
        verbose_name_plural = _("Promo Codes")

    def is_valid(self, cart_total=None):
        now = timezone.now()
        if not (self.active and self.valid_from <= now <= self.valid_to and self.used_count < self.max_usage_limit):
            return False
        if self.min_cart_value is not None and cart_total is not None:
            if cart_total < self.min_cart_value:
                return False
        return True

    def apply_usage(self):
        if self.used_count < self.max_usage_limit:
            self.used_count = models.F('used_count') + 1
            self.save(update_fields=['used_count'])
            return True
        return False

    def __str__(self):
        return f"{self.code} ({self.discount_percentage}%)"
    

class Promotion(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    banner_image = models.ImageField(upload_to='promotions/', blank=True, null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("Optional: General discount percentage for this promotion (e.g., 15 for 15%)"))
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    active = models.BooleanField(default=True)
    
    products = models.ManyToManyField(Product, blank=True, related_name='promotions', help_text=_("Link specific products to this promotion."))
    categories = models.ManyToManyField(Category, blank=True, related_name='promotions', help_text=_("Link specific categories to this promotion."))

    class Meta:
        ordering = ['-start_date']
        verbose_name = _("Promotion")
        verbose_name_plural = _("Promotions")

    def is_active_now(self):
        now = timezone.now()
        return self.active and self.start_date <= now <= self.end_date

    def __str__(self):
        return self.name

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending_payment', _('Pending Payment')),
        ('processing', _('Processing')),
        ('shipped', _('Shipped')),
        ('delivered', _('Delivered')),
        ('cancelled', _('Cancelled')),
        ('failed', _('Failed')),
        ('refunded', _('Refunded')),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=False, help_text=_("Customer who placed the order. Required."))
    order_id_display = models.CharField(_("Order ID (Display)"), max_length=20, unique=True, blank=True, help_text=_("User-friendly order ID, can be generated.")) 
    
    promo_code_applied = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders", verbose_name=_("Promo Code Applied"))
    discount_amount = models.DecimalField(_("Discount Amount"), max_digits=10, decimal_places=2, default=0)
    
    subtotal_price = models.DecimalField(_("Subtotal Price"), max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(_("Shipping Fee"), max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(_("Grand Total Price"), max_digits=10, decimal_places=2)
    
    shipping_full_name = models.CharField(_("Full Name"), max_length=255)
    shipping_address_line1 = models.CharField(_("Address Line 1"), max_length=255)
    shipping_address_line2 = models.CharField(_("Address Line 2"), max_length=255, blank=True, null=True)
    shipping_city = models.CharField(_("City"), max_length=100)
    shipping_postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True, null=True)
    shipping_country = models.CharField(_("Country"), max_length=100, default="Egypt")
    
    contact_phone = models.CharField(_("Contact Phone"), max_length=20)
    contact_email = models.EmailField(_("Contact Email"), max_length=254)
    
    order_notes = models.TextField(_("Order Notes"), blank=True, null=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending_payment', db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    payment_method = models.CharField(_("Payment Method"), max_length=50, blank=True, null=True)
    payment_id = models.CharField(_("Payment ID/Transaction ID"), max_length=100, blank=True, null=True, db_index=True)
    is_paid = models.BooleanField(_("Is Paid"), default=False, db_index=True)
    paid_at = models.DateTimeField(_("Paid At"), null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def save(self, *args, **kwargs):
        if not self.order_id_display:
            import uuid
            self.order_id_display = f"MBA-{str(uuid.uuid4()).split('-')[0].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_id_display or self.id} by {self.customer}"
        

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    
    product_name = models.CharField(_("Product Name"), max_length=255, help_text=_("Snapshot of product name at time of order."))
    variant_details = models.CharField(_("Variant Details"), max_length=255, blank=True, null=True, help_text=_("e.g., Size: M, Color: Red"))
    
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price_at_purchase = models.DecimalField(_("Price at Purchase (per unit)"), max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ('order', 'product', 'variant')
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    def get_total_price(self):
        return self.price_at_purchase * self.quantity
            
    def __str__(self):
        return f"{self.quantity} x {self.product_name or 'N/A'} for Order {self.order.order_id_display or self.order.id}"
    
    def save(self, *args, **kwargs):
        # Populate snapshot fields if not already set (e.g., on creation)
        if not self.product_name and self.product:
            self.product_name = self.product.name
        if not self.variant_details and self.variant:
            self.variant_details = f"Size: {self.variant.size}" # Add more details if variant has color etc.
        # Price at purchase should be set when item is added to order
        super().save(*args, **kwargs)

class NewsletterSubscription(models.Model):
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Newsletter Subscription")
        verbose_name_plural = _("Newsletter Subscriptions")
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email

class Question(models.Model):
    product = models.ForeignKey(Product, related_name='questions', on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, related_name='questions_asked', on_delete=models.SET_NULL, null=True, blank=True)
    user_name_display = models.CharField(_("Display Name for Question"), max_length=150, blank=True, help_text=_("Name shown with the question if customer is anonymous or prefers different name."))
    
    text = models.TextField(_("Question Text"))
    answer_text = models.TextField(_("Answer Text"), blank=True, null=True)
    
    created_at = models.DateTimeField(_("Asked At"), auto_now_add=True, db_index=True)
    answered_at = models.DateTimeField(_("Answered At"), null=True, blank=True)
    answered_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='questions_answered', on_delete=models.SET_NULL, null=True, blank=True, help_text=_("Staff user who answered."))
    
    is_approved = models.BooleanField(_("Approved"), default=False, help_text=_("Is the question (and answer) approved to be shown?"))
    is_answered = models.BooleanField(_("Answered"), default=False, editable=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Product Question")
        verbose_name_plural = _("Product Questions")

    def save(self, *args, **kwargs):
        if self.answer_text and not self.answered_at:
            self.answered_at = timezone.now()
        self.is_answered = bool(self.answer_text and self.answered_at)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Q: {self.text[:50]}... for {self.product.name}"

class Video(models.Model):
    product = models.ForeignKey(Product, related_name='videos', on_delete=models.CASCADE)
    video_url = models.URLField(_("Video URL"), max_length=1000)
    video_title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _("Product Video")
        verbose_name_plural = _("Product Videos")

    def __str__(self):
        return self.video_title or f"Video for {self.product.name}"
