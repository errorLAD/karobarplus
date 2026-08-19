from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.views import View
from django.contrib.auth.models import User
from .models import Business, UserProfile
from .forms import RegistrationForm, LoginForm

class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        form = RegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            b_name = form.cleaned_data['business_name']
            owner_name = form.cleaned_data['owner_name']
            phone = form.cleaned_data['phone']
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Create Business
            business = Business.objects.create(
                name=b_name,
                owner_name=owner_name,
                phone=phone,
                email=email
            )

            # Create User
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=owner_name
            )

            # Create UserProfile
            UserProfile.objects.create(
                user=user,
                business=business,
                role='Owner',
                phone=phone
            )

            # Initialize Default Business Settings & WhatsApp Templates
            try:
                from settings_app.models import BusinessSettings
                from whatsapp.models import WhatsAppMessageTemplate
                
                BusinessSettings.objects.get_or_create(
                    business=business,
                    defaults={
                        'upi_id': f"{phone}@upi",
                        'payee_name': b_name,
                        'reminder_before_due_days': 2,
                        'followup_frequency_days': 3
                    }
                )

                WhatsAppMessageTemplate.objects.get_or_create(
                    business=business,
                    trigger_type='Due Reminder',
                    defaults={
                        'title': 'Friendly Due Reminder',
                        'content': 'Namaste {{customer_name}}, {{business_name}} se aapka balance {{amount}} due hai on {{due_date}}. Kripya samay par bhugtan karein. UPI: {{upi_id}}'
                    }
                )
                WhatsAppMessageTemplate.objects.get_or_create(
                    business=business,
                    trigger_type='Overdue Reminder',
                    defaults={
                        'title': 'Overdue Payment Followup',
                        'content': 'Namaste {{customer_name}}, aapka {{amount}} ka udhaar balance overdue ho chuka hai. Kripya is link se pay karein: {{payment_link}}'
                    }
                )
                WhatsAppMessageTemplate.objects.get_or_create(
                    business=business,
                    trigger_type='Payment Link',
                    defaults={
                        'title': 'UPI Payment Link',
                        'content': 'Namaste {{customer_name}}, aap yahan payment kar sakte hain: {{payment_link}} ya UPI ID: {{upi_id}} par pay kar confirmation bhej de.'
                    }
                )
            except Exception:
                pass

            login(request, user)
            messages.success(request, f"Welcome to KarobarPlus, {b_name}!")
            return redirect('dashboard:index')

        return render(request, 'accounts/register.html', {'form': form})

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser or request.user.is_staff:
                return redirect('platform_admin:dashboard')
            return redirect('dashboard:index')
        form = LoginForm()
        return render(request, 'accounts/login.html', {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                if user.is_superuser or user.is_staff:
                    return redirect('platform_admin:dashboard')
                return redirect('dashboard:index')
            else:
                messages.error(request, "Invalid username or password.")
        return render(request, 'accounts/login.html', {'form': form})

class LogoutView(View):
    def post(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('accounts:login')
