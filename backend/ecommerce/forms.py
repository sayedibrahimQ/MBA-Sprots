from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Customer, Review, Question, Order # Assuming Order form might be needed for profile/checkout modifications

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')
    first_name = forms.CharField(max_length=30)
    second_name = forms.CharField(max_length=30) # Changed from last_name for consistency
    phone = forms.CharField(max_length=20)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'second_name')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create or update customer profile
            Customer.objects.update_or_create(
                user=user,
                defaults={
                    'first_name': self.cleaned_data.get('first_name'),
                    'second_name': self.cleaned_data.get('second_name'),
                    'email': self.cleaned_data.get('email'),
                    'phone': self.cleaned_data.get('phone')
                }
            )
        return user

class CustomLoginForm(AuthenticationForm):
    # You can customize this if your login.html has specific needs
    # For now, it will behave like the default AuthenticationForm
    pass

class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=200, required=False)
    second_name = forms.CharField(max_length=200, required=False)
    email = forms.EmailField(required=True) # Make email required
    phone = forms.CharField(max_length=20, required=True)
    phone2 = forms.CharField(max_length=20, required=False)
    fullAddress = forms.CharField(max_length=200, required=False, label='Full Address')
    city = forms.CharField(max_length=200, required=False)

    class Meta:
        model = Customer
        fields = ['first_name', 'second_name', 'email', 'phone', 'phone2', 'fullAddress', 'city']

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['review_text', 'rating'] # Add 'img' if you want image uploads with reviews
        widgets = {
            'review_text': forms.Textarea(attrs={'rows': 4}),
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5})
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ask your question here...'}) # Added placeholder
        }

class OrderUpdateForm(forms.ModelForm): # Example if you allow users to update parts of an order, e.g., address before shipping
    # This is a placeholder, tailor fields based on what users can actually modify
    class Meta:
        model = Order
        fields = ['shipping_address_line1','shipping_address_line2', 'shipping_city', 'contact_phone', 'order_notes'] 