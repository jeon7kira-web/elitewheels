from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .models import (
    Profile,
    Car,
    Booking,
    Brand,
    Review,
    Feature,
    Favorite,
    Location,
)
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta    
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Case, When, Value, IntegerField
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

    cars = Car.objects.select_related(
    'brand'
).prefetch_related(
    'features',
    'reviews'
)
    # ---------------- FILTER AVAILABLE CARS ----------------
    if pickup and dropoff:

        pickup_date = date.fromisoformat(pickup)
        dropoff_date = date.fromisoformat(dropoff)

        booked_cars = Booking.objects.filter(
            Q(pickup_date__lt=dropoff_date) &
            Q(dropoff_date__gt=pickup_date),
            status__in=['pending', 'confirmed', 'active']
        ).values_list("car_id", flat=True)

        cars = cars.exclude(id__in=booked_cars)

    # ---------------- FILTERS ----------------
    brand_filter = request.GET.get("brand")
    type_filter = request.GET.get("type")
    transmission_filter = request.GET.get("transmission")

    if brand_filter:
        cars = cars.filter(brand__name=brand_filter)

    if type_filter:
        cars = cars.filter(car_type=type_filter)

    if transmission_filter:
        cars = cars.filter(transmission=transmission_filter)

    # ---------------- FILTER OPTIONS ----------------

    types = Car.objects.values_list(
        'car_type',
        flat=True
    ).distinct()

    transmissions = Car.objects.values_list(
        'transmission',
        flat=True
    ).distinct()

    return render(request, "myapp/ourfleet.html", {
        "cars": cars,
        "types": types,
        "transmissions": transmissions,
        "pickup_date": pickup,
        "dropoff_date": dropoff,
    })

def car_details(request, car_id):

    car = get_object_or_404(
        Car.objects.select_related('brand').prefetch_related(
            'images',
            'features',
            'reviews__user'
        ),
        id=car_id
    )

    # ---------------- DISABLED DATES ----------------
    bookings = Booking.objects.filter(
        car=car,
        status__in=["pending", "confirmed", "active"]
    )

    disabled_dates_list = []

    for b in bookings:

        current = b.pickup_date

        while current <= b.dropoff_date:
            disabled_dates_list.append(
                current.strftime("%Y-%m-%d")
            )

            current += timedelta(days=1)

    # ---------------- RELATED CARS ----------------
    related_cars = Car.objects.filter(
        brand=car.brand
    ).exclude(id=car.id)[:3]

    # ---------------- REVIEWS ----------------
    reviews = Review.objects.filter(
        car=car
    ).select_related('user').order_by('-created_at')

    # ---------------- BOOKING REDIRECT ----------------
    if request.method == "POST":

        date_range = request.POST.get("date_range")

        if date_range and " to " in date_range:

            pickup, dropoff = date_range.split(" to ")

            request.session["pickup_date"] = pickup
            request.session["dropoff_date"] = dropoff

            return redirect(
                "book_car",
                car_id=car.id
            )
    related_cars = Car.objects.filter(
        car_type=car.car_type
    ).exclude(id=car.id)[:3]
    return render(request, "myapp/cardetails.html", {
    "car": car,
    "disabled_dates": json.dumps(disabled_dates_list),
    "related_cars": related_cars,
})

@login_required(login_url='/auth/')
def book_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    pickup = request.session.get("pickup_date")
    dropoff = request.session.get("dropoff_date")

    # Calculate totals for the summary
    total_days = 0
    total_price = 0
    if pickup and dropoff:
        pickup_date = date.fromisoformat(pickup)
        dropoff_date = date.fromisoformat(dropoff)
        total_days = max(
        1,
        (dropoff_date - pickup_date).days
)
        total_price = total_days * car.price_per_day

    if request.method == "POST":
        pickup = request.POST.get("pickup_date") or pickup
        dropoff = request.POST.get("dropoff_date") or dropoff

        if not pickup or not dropoff:
            return redirect("car_details", car_id=car.id)

        pickup_date = date.fromisoformat(pickup)
        dropoff_date = date.fromisoformat(dropoff)
        total_days = (dropoff_date - pickup_date).days

        if total_days <= 0:
            return redirect("car_details", car_id=car.id)

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
        "pickup_date": pickup,
        "dropoff_date": dropoff,
        "total_days": total_days,
        "total_price": total_price,
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

    bookings = list(
    Booking.objects
    .filter(user=user)
    .select_related('car')
    )

    groups = {
    "active": [],
    "confirmed": [],
    "pending": [],
    "cancelled": [],
    "completed": [],
    }

    for b in bookings:
        groups[b.status_auto].append(b)

    if request.method == "POST":

        # -------- PROFILE UPDATE --------
        if "update_profile" in request.POST:
            user.first_name = request.POST.get("first_name", "")
            user.last_name = request.POST.get("last_name", "")
            user.email = request.POST.get("email", "")
            profile.phone = request.POST.get("phone", "")

            if request.FILES.get("license"):
                profile.license = request.FILES["license"]

            user.save()
            profile.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("dashboard")

        # -------- PASSWORD CHANGE --------
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
    favorites = Favorite.objects.filter(
            user=user
        ).select_related('car')
    active_bookings = [
      b for b in bookings if b.status_auto == "active"
]

    completed_bookings = [
        b for b in bookings if b.status_auto == "completed"
    ]
    return render(request, "myapp/dashboard.html", {
        "profile": profile,
        "groups": groups,
        "active_bookings":active_bookings,
        "completed_bookings":completed_bookings,
        "favorites": favorites,
    })

@login_required
def cancel_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(
            Booking,
            id=booking_id,
            user=request.user
        )

        booking.status = "cancelled"
        booking.save()

        return JsonResponse({
            "success": True,
            "new_status": booking.status_auto
        })

    return JsonResponse({"success": False}, status=400)

@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    return render(request, "myapp/booking_detail.html", {
        "booking": booking
    })

@login_required(login_url='/auth/')
def add_review(request, car_id):

    car = get_object_or_404(Car, id=car_id)

    if request.method == "POST":

        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        # Prevent duplicate reviews
        existing_review = Review.objects.filter(
            user=request.user,
            car=car
        ).first()

        if existing_review:
            messages.error(
                request,
                "You already reviewed this car."
            )
            return redirect("car_details", car_id=car.id)

        Review.objects.create(
            user=request.user,
            car=car,
            rating=rating,
            comment=comment
        )

        messages.success(
            request,
            "Review added successfully!"
        )

    return redirect("car_details", car_id=car.id)

@login_required(login_url='/auth/')
def toggle_favorite(request, car_id):

    car = get_object_or_404(Car, id=car_id)

    favorite = Favorite.objects.filter(
        user=request.user,
        car=car
    )

    if favorite.exists():
        favorite.delete()
    else:
        Favorite.objects.create(
            user=request.user,
            car=car
        )

    return redirect("car_details", car_id=car.id)