from django.contrib import admin
from .models import (
    Product, ProductVariant, ProductType, Category, ProductImage, Customer,
    Review, Cart, CartItem, DeliveryFees, PromoCode, Promotion, Order, OrderItem,
    NewsletterSubscription, Question, Video, Team
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'product_type', 'price', 'display_price', 'is_active', 'best_selling', 'created_at')
    list_editable = ('is_active', 'best_selling')
    list_filter = ('is_active', 'category', 'product_type', 'best_selling')
    search_fields = ('name', 'description')
    inlines = [ProductVariantInline, ProductImageInline]
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {}
    # filter_horizontal = ('promotions',)

class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'quantity', 'additional_price', 'get_price')
    list_filter = ('product',)
    search_fields = ('product__name', 'size')


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'alt_text')
    search_fields = ('product__name', 'alt_text')


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'phone', 'email', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    list_filter = ('created_at',)


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user_name', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating')
    search_fields = ('product__name', 'user_name', 'review_text')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('added_at',)


class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'device_token', 'number_of_items', 'total_price', 'created_at', 'updated_at')
    search_fields = ('user__username', 'device_token')
    list_filter = ('created_at',)
    inlines = [CartItemInline]


class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'variant', 'quantity', 'get_total_price', 'added_at')
    search_fields = ('cart__user__username', 'product__name', 'variant__size')
    list_filter = ('added_at',)


class DeliveryFeesAdmin(admin.ModelAdmin):
    list_display = ('city', 'delivery_fee')
    search_fields = ('city',)


class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'active', 'valid_from', 'valid_to', 'used_count', 'max_usage_limit')
    list_filter = ('active',)
    search_fields = ('code',)


class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_percentage', 'start_date', 'end_date', 'active')
    list_filter = ('active',)
    search_fields = ('name', 'description')
    filter_horizontal = ('products', 'categories')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price_at_purchase', 'product_name', 'variant_details')


class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id_display', 'customer', 'status', 'total_price', 'is_paid', 'created_at')
    search_fields = ('order_id_display', 'customer__user__username', 'contact_email', 'contact_phone')
    list_filter = ('status', 'is_paid', 'created_at')
    inlines = [OrderItemInline]


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'variant_details', 'quantity', 'price_at_purchase')
    search_fields = ('order__order_id_display', 'product_name', 'variant_details')


class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_active', 'subscribed_at')
    search_fields = ('email', 'name')
    list_filter = ('is_active', 'subscribed_at')


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('product', 'user_name_display', 'is_approved', 'is_answered', 'created_at', 'answered_at')
    search_fields = ('product__name', 'user_name_display', 'text', 'answer_text')
    list_filter = ('is_approved', 'is_answered', 'created_at')


class VideoAdmin(admin.ModelAdmin):
    list_display = ('product', 'video_title', 'video_url', 'uploaded_at')
    search_fields = ('product__name', 'video_title', 'video_url')
    list_filter = ('uploaded_at',)


admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariant, ProductVariantAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ProductType, ProductTypeAdmin)
admin.site.register(ProductImage, ProductImageAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem, CartItemAdmin)
admin.site.register(DeliveryFees, DeliveryFeesAdmin)
admin.site.register(PromoCode, PromoCodeAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(NewsletterSubscription, NewsletterSubscriptionAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(Team)