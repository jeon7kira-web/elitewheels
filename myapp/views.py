from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from datetime import date, timedelta
import json

from .models import Profile, Car, Booking, Review, Favorite, Brand


# =========================================================
# STATIC PAGES
# =========================================================
def home(request):
    return render(request, 'myapp/home.html')

def auth_view(request):
    return render(request, 'myapp/auth.html')

def faq_view(request):
    return render(request, 'myapp/faq.html')

def contact_view(request):
    return render(request, 'myapp/contact.html')

def about_view(request):
    return render(request, 'myapp/about.html')


# =========================================================
# REGISTER
# =========================================================
def register_view(request):
    if request.method == 'POST':
        full_name  = request.POST.get('full_name', '').strip()
        email      = request.POST.get('email', '').strip()
        phone      = request.POST.get('phone', '').strip()
        password   = request.POST.get('password', '')
        confirm    = request.POST.get('confirm_password', '')
        license_f  = request.FILES.get('license')

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('auth')

        if User.objects.filter(username=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('auth')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name,
        )

        Profile.objects.get_or_create(
            user=user,
            defaults={"phone": phone, "license": license_f},
        )

        login(request, user)
        return redirect('dashboard')

    return redirect('home')


# =========================================================
# LOGIN / LOGOUT
# =========================================================
def login_view(request):
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('home')

        messages.error(request, "Invalid email or password.")
        return redirect('auth')

    return redirect('auth')


def logout_view(request):
    logout(request)
    return redirect('home')


# =========================================================
# FLEET
# =========================================================
def fleet(request):
    pickup  = request.GET.get("pickup_date")
    dropoff = request.GET.get("dropoff_date")

    cars = Car.objects.select_related('brand').prefetch_related('features', 'reviews')

    if pickup and dropoff:
        try:
            pickup_date  = date.fromisoformat(pickup)
            dropoff_date = date.fromisoformat(dropoff)

            booked = Booking.objects.filter(
                Q(pickup_date__lt=dropoff_date) &
                Q(dropoff_date__gt=pickup_date),
                status__in=['pending', 'confirmed', 'active'],
            ).values_list("car_id", flat=True)

            cars = cars.exclude(id__in=booked)
        except ValueError:
            pickup = dropoff = None

    return render(request, "myapp/ourfleet.html", {
        "cars":          cars,
        "brands":        Brand.objects.all(),                                           # FIX: was missing
        "types":         Car.objects.values_list('car_type', flat=True).distinct(),
        "transmissions": Car.objects.values_list('transmission', flat=True).distinct(),
        "pickup_date":   pickup,
        "dropoff_date":  dropoff,
    })


# =========================================================
# CAR DETAILS
# =========================================================
def car_details(request, car_id):
    car = get_object_or_404(
        Car.objects.select_related('brand').prefetch_related(
            'images', 'features', 'reviews__user'
        ),
        id=car_id,
    )

    bookings = Booking.objects.filter(
        car=car,
        status__in=["pending", "confirmed", "active"],
    )

    disabled_dates = []
    for b in bookings:
        current = b.pickup_date
        while current <= b.dropoff_date:
            disabled_dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

    related_cars = Car.objects.filter(brand=car.brand).exclude(id=car.id)[:3]

    if request.method == "POST":
        date_range = request.POST.get("date_range", "")
        if " to " in date_range:
            pickup, dropoff = date_range.split(" to ", 1)
            request.session["pickup_date"]  = pickup.strip()
            request.session["dropoff_date"] = dropoff.strip()
            return redirect("book_car", car_id=car.id)

    return render(request, "myapp/cardetails.html", {
        "car":            car,
        "disabled_dates": json.dumps(disabled_dates),
        "related_cars":   related_cars,
    })


# =========================================================
# BOOK CAR
# =========================================================
@login_required(login_url='/auth/')
def book_car(request, car_id):
    car = Car.objects.get(id=car_id)

    pickup = request.session.get("pickup_date")
    dropoff = request.session.get("dropoff_date")

    # Calculate totals for the summary
    total_days = 0
    total_price = 0
    if pickup and dropoff:
        pickup_date = date.fromisoformat(pickup)
        dropoff_date = date.fromisoformat(dropoff)
        total_days = (dropoff_date - pickup_date).days
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


# =========================================================
# CONFIRMATION
# =========================================================
def confirmation_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, "myapp/confirmation.html", {"booking": booking})


# =========================================================
# BOOKING DETAIL  ← FIX: was missing entirely
# =========================================================
@login_required(login_url='/auth/')
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "myapp/booking_detail.html", {"booking": booking})


# =========================================================
# DASHBOARD
# =========================================================
@login_required(login_url='/auth/')
def dashboard_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    # ── Profile update ────────────────────────────────────
    if request.method == "POST" and "update_profile" in request.POST:
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name  = request.POST.get("last_name",  "").strip()
        new_email = request.POST.get("email", "").strip()

        if new_email and new_email != user.email:
            if User.objects.filter(username=new_email).exclude(pk=user.pk).exists():
                messages.error(request, "That email is already in use.")
            else:
                user.email    = new_email
                user.username = new_email

        user.save()
        profile.phone = request.POST.get("phone", "").strip()

        if request.FILES.get("license"):
            profile.license = request.FILES["license"]

        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("dashboard")

    # ── Password change ───────────────────────────────────
    if request.method == "POST" and "change_password" in request.POST:
        old_pw  = request.POST.get("old_password", "")
        new_pw  = request.POST.get("new_password", "")
        confirm = request.POST.get("confirm_password", "")

        if not user.check_password(old_pw):
            messages.error(request, "Current password is incorrect.")
        elif new_pw != confirm:
            messages.error(request, "New passwords do not match.")
        elif len(new_pw) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        else:
            user.set_password(new_pw)
            user.save()
            update_session_auth_hash(request, user)   # keep user logged in
            messages.success(request, "Password updated successfully.")

        return redirect("dashboard")

    # ── Build booking groups using status_auto ────────────
    all_bookings = Booking.objects.filter(user=user).select_related('car')

    groups = {
        "active":    [],
        "confirmed": [],
        "pending":   [],
        "cancelled": [],
        "completed": [],
    }

    total_spent = 0

    for b in all_bookings:
        status_key = b.status_auto                      # FIX: use property correctly
        if status_key in groups:
            groups[status_key].append(b)
        if b.total_price and b.status_auto != "cancelled":
            total_spent += b.total_price

    return render(request, "myapp/dashboard.html", {
        "profile":           profile,
        "groups":            groups,
        "active_bookings":   groups["active"],
        "completed_bookings":groups["completed"],
        "total_spent":       total_spent,
    })


# =========================================================
# CANCEL BOOKING
# =========================================================
@login_required
def cancel_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        if booking.status_auto in ("active", "completed"):
            return JsonResponse({"success": False, "error": "Cannot cancel this booking."}, status=400)

        booking.status = "cancelled"
        booking.save()

        return JsonResponse({"success": True, "new_status": "cancelled"})

    return JsonResponse({"success": False, "error": "Invalid method."}, status=400)


# =========================================================
# REVIEW
# =========================================================
@login_required(login_url='/auth/')
def add_review(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    if request.method == "POST":
        if Review.objects.filter(user=request.user, car=car).exists():
            messages.error(request, "You have already reviewed this car.")
            return redirect("cardetails", car_id=car.id)

        rating  = request.POST.get("rating")
        comment = request.POST.get("comment", "").strip()

        if not rating or not comment:
            messages.error(request, "Rating and comment are required.")
            return redirect("cardetails", car_id=car.id)

        Review.objects.create(
            user=request.user,
            car=car,
            rating=int(rating),
            comment=comment,
        )
        messages.success(request, "Review submitted successfully.")

    return redirect("cardetails", car_id=car.id)


# =========================================================
# FAVORITE
# =========================================================
@login_required
def toggle_favorite(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    fav = Favorite.objects.filter(user=request.user, car=car)

    if fav.exists():
        fav.delete()
    else:
        Favorite.objects.create(user=request.user, car=car)

    return redirect("cardetails", car_id=car.id)