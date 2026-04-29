from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .models import Profile, Car, Booking
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta    
import json
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date



def home(request):
    return render(request, 'myapp/home.html')


def auth_view(request):
    return render(request, 'myapp/auth.html')


def faq_view(request):
    return render(request, 'myapp/faq.html')


def contact_view(request):
    return render(request, 'myapp/contact.html')


def about_view(request):
    return render(request, 'myapp/#about')


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


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('home')
    return redirect('home')


def fleet(request):
    pickup = request.GET.get("pickup_date")
    dropoff = request.GET.get("dropoff_date")

    cars = Car.objects.all()

    if pickup and dropoff:
        pickup_date = date.fromisoformat(pickup)
        dropoff_date = date.fromisoformat(dropoff)

        booked_cars = Booking.objects.filter(
            Q(pickup_date__lt=dropoff_date) &
            Q(dropoff_date__gt=pickup_date),
            status__in=['pending', 'confirmed', 'active']
        ).values_list("car_id", flat=True)

        cars = cars.exclude(id__in=booked_cars)

    brands = Car.objects.values_list('brand', flat=True).distinct()
    types = Car.objects.values_list('car_type', flat=True).distinct()
    transmissions = Car.objects.values_list('transmission', flat=True).distinct()

    return render(request, "myapp/ourfleet.html", {
        "cars": cars,
        "brands": brands,
        "types": types,
        "transmissions": transmissions,
        "pickup_date": pickup,
        "dropoff_date": dropoff,
    })


def car_details(request, car_id):
    car = Car.objects.get(id=car_id)

    if request.method == "POST":
        pickup = request.POST.get("pickup_date")
        dropoff = request.POST.get("dropoff_date")

        request.session["pickup_date"] = pickup
        request.session["dropoff_date"] = dropoff

        return redirect(f"/book/{car.id}/")

    return render(request, "myapp/cardetails.html", {
        "car": car
    })


from datetime import date, timedelta
import json

@login_required(login_url='/auth/')
def book_car(request, car_id):
    car = Car.objects.get(id=car_id)

    bookings = Booking.objects.filter(
        car=car,
        status__in=["pending", "confirmed", "active"]
    )

    disabled_dates_list = []

    for b in bookings:
        current = b.pickup_date
        while current <= b.dropoff_date:
            disabled_dates_list.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

    if request.method == "POST":
        date_range = request.POST.get("date_range")

        if not date_range:
            return redirect("cardetails", car_id=car.id)

        pickup, dropoff = date_range.split(" to ")

        pickup_date = date.fromisoformat(pickup)
        dropoff_date = date.fromisoformat(dropoff)

        total_days = (dropoff_date - pickup_date).days

        if total_days <= 0:
            raise ValidationError("Invalid date range")

        booking = Booking.objects.create(
            user=request.user,
            car=car,
            pickup_date=pickup_date,
            dropoff_date=dropoff_date,
            with_driver=request.POST.get("with_driver") == "on"
        )

        return redirect("confirmation", booking_id=booking.id)

    return render(request, "myapp/booking.html", {
        "car": car,
        "disabled_dates": json.dumps(disabled_dates_list),
    })
def confirmation_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    return render(request, "myapp/confirmation.html", {
        "booking": booking
    }) 

@login_required(login_url='/auth/')
def dashboard_view(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    today = timezone.now().date()

    bookings = Booking.objects.filter(user=user).select_related('car').order_by('-pickup_date')
    active_bookings = bookings.filter(dropoff_date__gte=today)
    completed_bookings = bookings.filter(dropoff_date__lt=today)

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
        "profile": profile,
        "active_bookings": active_bookings,
        "completed_bookings": completed_bookings,
    })


@login_required
def cancel_booking(request, booking_id):
    booking = Booking.objects.get(id=booking_id, user=request.user)
    booking.status = 'cancelled'
    booking.save()
    messages.success(request, "Booking cancelled")
    return redirect("dashboard")    


