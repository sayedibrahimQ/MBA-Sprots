from django.db import models
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from PIL import Image as mg
from PIL import ImageFilter
import os
from django.conf import settings

class Size(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)  # Renamed from 'product_re'
    size = models.CharField(max_length=255, default='Large')
    
    def __str__(self):
        return f'{self.product.name} \t {self.size}'
# # Desired dimensions
# MIN_HEIGHT = 500
# MAX_HEIGHT = 1000
# MIN_WIDTH = 500
# MAX_WIDTH = 1000

# TARGET_HEIGHT = 800  # Example target height
# TARGET_WIDTH = 800   # Example target width

from io import BytesIO
from django.core.files.base import ContentFile
class Product(models.Model):
    type_choices = (
        ('Shirt', 'Shirt'),
        ('T-Shirt', 'T-Shirt'),
        ('Jacket', 'Jacket'),
        ('Pullover', 'Pullover'),
        ('Pant', 'Pant'),
        ('Hoodie', 'Hoodie'),
        ('Sweater', 'Sweater'),
        ('Shoes', 'Shoes'),
        ('Watch', 'Watch'),
    )
    
    categories = (
        ('Clothes', 'Clothes'),
        ('CareProducts', 'CareProducts'),
        ('Accessories', 'Accessories'),
    )
    id = models.IntegerField(auto_created=True, primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.BooleanField(blank=True)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=255)
    sizes = models.BooleanField(default=False, unique=False, blank=True)
    description = models.TextField()
    img = models.ImageField(upload_to='products/')
    img1 = models.ImageField(upload_to='products/', blank=True, null=True)
    img2 = models.ImageField(upload_to='products/', blank=True, null=True)
    img3 = models.ImageField(upload_to='products/', blank=True, null=True)
    type = models.CharField(choices=type_choices, max_length=255)
    category = models.CharField(choices=categories, max_length=255)
    quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    best_selling = models.BooleanField(null=True, blank=True)
        
    def compress_image(self, uploaded_image):
        from PIL import Image
        image_temp = Image.open(uploaded_image)
        output_io_stream = BytesIO()
        image_temp = image_temp.convert('RGB')
        max_size = (800, 800)
        image_temp.thumbnail(max_size, Image.Resampling.LANCZOS)

        image_temp.save(output_io_stream, format='WEBP', quality=85)
        output_io_stream.seek(0)
        uploaded_image = ContentFile(output_io_stream.read(), name=uploaded_image.name.split('.')[0] + '.webp')
        return uploaded_image
    
    def __str__(self):
        return f'{self.name} \t {self.id}'
    
    def save(self, *args, **kwargs):
        # Process the images before saving
        if self.img:
            self.img = self.compress_image(self.img)
        if self.img1:
            self.img1 = self.compress_image(self.img1)
        if self.img2:
            self.img2 = self.compress_image(self.img2)
        if self.img3:
            self.img3 = self.compress_image(self.img3)
        super().save(*args, **kwargs)
    
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    device_token = models.CharField(max_length=300, blank=True, null=True)
    first_name = models.CharField(max_length=200, blank=True)
    second_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20)
    phone2 = models.CharField(max_length=20, blank= True)
    fullAddress = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    date_modified = models.DateTimeField(User, auto_now=True)
    email = models.EmailField( max_length=254)

    def __str__(self):
        return f"{self.first_name}  \t  {self.second_name}"


class Category(models.Model):
    category = models.CharField(max_length=255)
    def __str__(self):
        return self.category

class Image(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='Products/')

    def __str__(self):
        return self.product.name


class Review(models.Model):
    # foreign key to the Product model
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # foreign key to the user model
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.TextField()
    rating = models.IntegerField()
    img = models.ImageField(upload_to= 'customers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
            return self.product.name
        

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    device_token = models.CharField(max_length=255, null=True, blank=True, unique = True)  # To identify guest users by device token
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.IntegerField(default = 0)
    number_of_items = models.IntegerField(default = 0)
    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        else:
            return f"Cart for Device Token {self.device_token}"
        

# models.py

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True)
    color = models.CharField(max_length=25, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    
    def get_total_price(self):
        if self.product.discount:
            return self.product.new_price * self.quantity
        else:
            return self.product.price * self.quantity
            
    class Meta:
        unique_together = ('cart', 'product', 'size', 'color')  # Ensure uniqueness
        
class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_sizes')
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

from django.utils import timezone

class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage discount (e.g., 10 for 10%)")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(default=1)  # Number of times a promo code can be used
    used_count = models.IntegerField(default=0)

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to and self.used_count < self.usage_limit

    def __str__(self):
        return self.code
    

# Order Model
class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    order_id = models.CharField(max_length=255, null=True, blank=True)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    fullAddress = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255, blank=True) 
    email = models.EmailField(max_length=254)
    note = models.TextField(max_length=900, blank= True)
    status = models.CharField(max_length=10, choices=ORDER_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.customer:
            return f"Order {self.id} by {self.customer.first_name}"
        else:
            return f"Order {self.id} (No customer info)"
        
        
# OrderItem Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=25, blank=True, null= True)
    color = models.CharField(max_length=25, blank=True, null= True)

    price = models.DecimalField(max_digits=10, decimal_places=2)  
    
    class Meta:
        unique_together = ('order', 'product', 'size', 'color')  # Ensure uniqueness
        
    def get_total_price(self):
        if self.product.discount:
            return self.quantity * self.product.new_price 
        else:
            return self.quantity * self.product.price 
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in order {self.order.id}"
    


    
class DeliveryFees(models.Model):
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    city = models.CharField(max_length=255)
    
    def __str__(self):
        return f"Delivery Fee: {self.delivery_fee} | City: {self.city}"
    
    

class Emails(models.Model):
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.name} | {self.email}"

class Question(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField(max_length=900)
    product = models.ForeignKey(Product, on_delete= models.CASCADE)
    
    def __str__(self):
        return f"Q: {self.question} | P: {self.product.name}"

class Video(models.Model):
    video_link = models.CharField(max_length=10000)
    video_title = models.CharField(max_length = 255)
    product = models.ForeignKey(Product, on_delete= models.CASCADE)
    

class Images(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='Products/')

    def __str__(self):
        return f'{self.product.name} \t {self.id}'
