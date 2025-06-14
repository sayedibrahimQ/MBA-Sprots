from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'ecommerce'

urlpatterns = [
    path('', views.index, name='index'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:id>/', views.product_detail, name='product_detail'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<str:category_name>/', views.products_by_category, name='products_by_category'),
    
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    
    path('checkout/', views.checkout, name='checkout'),
    path('order/history/', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    path('about/', views.about_us, name='about_us'),
    # path('offers/', views.offer_list, name='offer_list'),
    # path('offers/<int:id>/', views.offer_detail_view, name='offer_detail_view'),

    path('product/<int:product_id>/review/add/', views.add_review, name='add_review'),
    path('product/<int:product_id>/question/add/', views.add_question, name='add_question'),

    path('teams/', views.teams, name='teams'),
    # Placeholder for actual URL names from base.html if they differ significantly
    # path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    # path('terms-conditions/', views.terms_conditions_view, name='terms_conditions'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)