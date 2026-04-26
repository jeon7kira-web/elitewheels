from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .models import Profile, Car, Booking
from django.db.models import Q




def home(request):
    return render(request, 'myapp/home.html')


def auth_view(request):
    return render(request, 'myapp/auth.html')



def faq_view(request):
    return render(request,'myapp/faq.html')

def contact_view(request):
    return render(request,'myapp/contact.html')

def about_view(request):
    return render(request,'myapp/#about')





def register_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get("phone")
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        license_file = request.FILES.get('license')

        
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

        
        Profile.objects.create(
            user=user,
            phone=phone,
            license=license_file
        )

        login(request, user)
        return redirect('dashboard')

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
@login_required(login_url='/auth/')
def dashboard_view(request):
    user = request.user

    
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST":

        if "update_profile" in request.POST:
            user.first_name = request.POST.get("first_name")
            user.last_name = request.POST.get("last_name")
            user.email = request.POST.get("email")
            profile.phone = request.POST.get("phone")
            if request.FILES.get("license"):
                profile.license = request.FILES.get("license")
            user.save()
            profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("dashboard")
        
        if "change_password" in request.POST:
            old_password = request.POST.get("old_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not user.check_password(old_password):
                messages.error(request, "Old password is incorrect")
                return redirect("dashboard")

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match")
                return redirect("dashboard")

            user.set_password(new_password)
            user.save()
            
            update_session_auth_hash(request, user)

            messages.success(request, "Password changed successfully!")
            return redirect("dashboard")

    return render(request, "myapp/dashboard.html", {
        "profile": profile
    })

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')
    
    # views.py

def fleet(request):
    pickup = request.GET.get("pickup_date")
    dropoff = request.GET.get("dropoff_date")

    cars = Car.objects.all()

    if pickup and dropoff:
        booked_cars = Booking.objects.filter(
            Q(pickup_date__lt=dropoff) & Q(dropoff_date__gt=pickup)
        ).values_list("car_id", flat=True)

        cars = cars.exclude(id__in=booked_cars)

    brands = Car.objects.values_list('brand', flat=True).distinct()
    types = Car.objects.values_list('car_type', flat=True).distinct()
    transmissions = Car.objects.values_list('transmission', flat=True).distinct()

    return render(request, "myapp/ourfleet.html", {
        "cars": cars,
        "brands": brands,
        "types": types,
        "transmissions": transmissions
    })
    

    
@login_required
def book_car(request, car_id):
    if request.method == "POST":
        pickup = request.POST.get("pickup_date")
        dropoff = request.POST.get("dropoff_date")

        Booking.objects.create(
            user=request.user,
            car_id=car_id,
            pickup_date=pickup,
            dropoff_date=dropoff
        )

@login_required(login_url='/auth/')
def booking_view(request):
    return render(request,'myapp/booking.html')

def confirmation_view(request):
    return render(request,'myapp/confirmation.html')

