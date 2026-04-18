from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .models import Profile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


def home(request):
    return render(request,'myapp/home.html')

def auth_view(request):
    return render(request,'myapp/auth.html')

def register_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        license = request.FILES.get('license')
        phone=request.POST.get("phone")
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('auth')

        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already exists")
            return redirect('auth')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
    )

        user.first_name = full_name
        user.save()

        profile = Profile.objects.create(
            user=user,
            phone=phone,
            license=request.FILES.get('license')
        )

        login(request, user)
        return redirect('home')
                            
    return redirect('home')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('auth')

    return redirect('auth')

    from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    print(request.user, request.user.is_authenticated)
    return render(request, 'myapp/dashboard.html')

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')

