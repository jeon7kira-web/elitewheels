from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.db.models import Q
from reportlab.lib.colors import HexColor
from django.http import JsonResponse
from datetime import date, timedelta
from reportlab.pdfgen import canvas
from django.db.models import Count
from reportlab.lib.pagesizes import A4
import json

from .models import Profile, Car, Booking, Review, Favorite, Brand



# STATIC PAGES

def home(request):
    reviews = Review.objects.select_related("user", "car").order_by("-created_at")[:10]
    favorites_count = Favorite.objects.filter(user=request.user).count()
    types = Car.objects.values_list("car_type", flat=True).distinct()
    featured_cars = Car.objects.annotate(
    bookings_count=Count(
        "bookings",
        filter=Q(bookings__status="confirmed")
    )
).order_by("-bookings_count")[:4]
    return render(request, "myapp/home.html", {
        "reviews": reviews,
        "favorites_count": favorites_count,
        "types":types,
        "featured_cars": featured_cars,
    })
def auth_view(request):
    return render(request, 'myapp/auth.html')

def faq_view(request):
    favorites_count = Favorite.objects.filter(user=request.user).count()

    return render(request, "myapp/faq.html",{
       "favorites_count":favorites_count,           
    })

def contact_view(request):
    favorites_count = Favorite.objects.filter(user=request.user).count()
    return render(request, "myapp/contact.html",{
       "favorites_count":favorites_count,   
    })

def about_view(request):
    return render(request, 'myapp/about.html')



# REGISTER

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



# LOGIN / LOGOUT

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



# FLEET

def fleet(request):
    pickup  = request.GET.get("pickup_date")
    dropoff = request.GET.get("dropoff_date")
    car_type = request.GET.get("type")

    cars = Car.objects.select_related('brand').prefetch_related('features', 'reviews')

    favorites_count = Favorite.objects.filter(user=request.user).count()
    favorite_ids = set(
        Favorite.objects.filter(user=request.user)
        .values_list("car_id", flat=True)
    )

    if pickup and dropoff:
        try:
            pickup_date = date.fromisoformat(pickup)
            dropoff_date = date.fromisoformat(dropoff)

            booked = Booking.objects.filter(
                Q(pickup_date__lt=dropoff_date) &
                Q(dropoff_date__gt=pickup_date),
                status__in=['pending', 'confirmed', 'active'],
            ).values_list("car_id", flat=True)

            cars = cars.exclude(id__in=booked)

        except ValueError:
            pass

    if car_type:
        cars = cars.filter(car_type__iexact=car_type)

    return render(request, "myapp/ourfleet.html", {
        "cars": cars,
        "favorites_count": favorites_count,
        "favorite_ids": favorite_ids,
        "brands": Brand.objects.all(),
        "types": Car.objects.values_list('car_type', flat=True).distinct(),
        "transmissions": Car.objects.values_list('transmission', flat=True).distinct(),
        "pickup_date": pickup,
        "dropoff_date": dropoff,
    })
# CAR DETAILS

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
    favorite_ids = set(
        Favorite.objects.filter(user=request.user)
        .values_list("car_id", flat=True)
)
    if request.method == "POST":
        date_range = request.POST.get("date_range", "")
        if " to " in date_range:
            pickup, dropoff = date_range.split(" to ", 1)
            request.session["pickup_date"]  = pickup.strip()
            request.session["dropoff_date"] = dropoff.strip()
            return redirect("book_car", car_id=car.id)

    return render(request, "myapp/cardetails.html", {
        "car":            car,
        "favorite_ids": favorite_ids,
        "disabled_dates": json.dumps(disabled_dates),
        "related_cars":   related_cars,
    })



# BOOK CAR

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



# CONFIRMATION

def confirmation_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, "myapp/confirmation.html", {"booking": booking})



# BOOKING DETAIL  ← FIX: was missing entirely

@login_required(login_url='/auth/')
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, "myapp/booking_detail.html", {"booking": booking})



# DASHBOARD

@login_required(login_url='/auth/')
def dashboard_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

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
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully.")
        return redirect("dashboard")

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
        status_key = b.status_auto
        if status_key in groups:
            groups[status_key].append(b)
        if b.total_price and status_key != "cancelled":
            total_spent += b.total_price

    favorite_cars = (
        Car.objects
        .filter(favorited_by__user=request.user)
        .select_related("brand")
        .distinct()
    )
    favorite_ids = list(favorite_cars.values_list("id", flat=True))

    reviewed_car_ids = Review.objects.filter(
        user=request.user
    ).values_list("car_id", flat=True)

    return render(request, "myapp/dashboard.html", {
        "profile":            profile,
        "groups":             groups,
        "active_bookings":    groups["active"],
        "completed_bookings": groups["completed"],
        "total_spent":        total_spent,
        "favorite_cars":      favorite_cars,
        "favorite_ids":       favorite_ids,
        "reviewed_car_ids":   reviewed_car_ids,
    })
@login_required
@require_POST
def toggle_favorite(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        car=car
    )

    if not created:
        favorite.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({
        "success": True,
        "liked": liked,
        "car_id": car_id
    })


# CANCEL BOOKING

@login_required
def cancel_booking(request, booking_id):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid method."},
            status=400
        )

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    if booking.status in ("active", "completed", "cancelled"):
        return JsonResponse(
            {"success": False, "error": "Cannot cancel this booking."},
            status=400
        )

    booking.status = "cancelled"
    booking.save()

    return JsonResponse({
        "success": True,
        "new_status": booking.status
    })


# REVIEW

@login_required(login_url='/auth/')
def add_review(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    # Check if user completed a booking
    completed_booking = Booking.objects.filter(
    user=request.user,
    car=car
)

    completed_booking = any(
        booking.status_auto == "completed"
        for booking in completed_booking
    )

    if not completed_booking:
        messages.error(request, "You can only review cars you have completed booking.")
        return redirect("cardetails", car_id=car.id)

    if request.method == "POST":

        if Review.objects.filter(user=request.user, car=car).exists():
            messages.error(request, "You have already reviewed this car.")
            return redirect("cardetails", car_id=car.id)

        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "").strip()

        if not rating or not comment:
            messages.error(request, "Rating and comment are required.")
            return redirect("cardetails", car_id=car.id)

        rating = int(rating)

        if rating < 1 or rating > 5:
            messages.error(request, "Invalid rating.")
            return redirect("cardetails", car_id=car.id)

        Review.objects.create(
            user=request.user,
            car=car,
            rating=rating,
            comment=comment,
        )
        

        messages.success(request, "Review submitted successfully.")

    return redirect("dashboard", car_id=car.id)


# FAVORITE



def download_receipt(request, booking_id):

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        user=request.user
    )

    customer_name = (
        booking.user.get_full_name()
        if booking.user.get_full_name()
        else booking.user.username
    )

    chauffeur_name = (
        str(booking.chauffeur)
        if booking.chauffeur
        else "No Chauffeur"
    )

    response = HttpResponse(content_type='application/pdf')

    response['Content-Disposition'] = (
        f'attachment; filename="EliteWheels_Receipt_{booking.id}.pdf"'
    )

    # =========================================
    # PDF SETUP
    # =========================================
    p = canvas.Canvas(response, pagesize=A4)

    width, height = A4

    # =========================================
    # COLORS
    # =========================================
    gold = HexColor("#C8A45D")
    dark = HexColor("#111111")
    gray = HexColor("#666666")
    light = HexColor("#F7F7F7")
    white = HexColor("#FFFFFF")

    # =========================================
    # HEADER
    # =========================================
    p.setFillColor(dark)
    p.rect(0, height - 120, width, 120, fill=1, stroke=0)

    # Logo / Brand
    p.setFillColor(gold)
    p.setFont("Helvetica-Bold", 30)
    p.drawCentredString(width / 2, height - 60, "EliteWheels")

    p.setFont("Helvetica", 13)
    p.drawCentredString(
        width / 2,
        height - 85,
        "Luxury Car Rental Receipt"
    )

    # =========================================
    # WATERMARK
    # =========================================
    p.saveState()

    p.setFont("Helvetica-Bold", 60)
    p.setFillColor(HexColor("#F1F1F1"))

    p.translate(width / 2, height / 2)
    p.rotate(45)

    p.drawCentredString(0, 0, "ELITEWHEELS")

    p.restoreState()

    # =========================================
    # START POSITION
    # =========================================
    y = height - 170

    # =========================================
    # HELPER FUNCTION
    # =========================================
    def draw_section(title, data, y_position):

        # Section card
        p.setFillColor(light)
        p.roundRect(
            40,
            y_position - 25,
            width - 80,
            35,
            8,
            fill=1,
            stroke=0
        )

        # Section title
        p.setFillColor(gold)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(55, y_position - 5, title)

        y_position -= 50

        # Section content
        p.setFont("Helvetica", 12)

        for label, value in data:

            p.setFillColor(gray)
            p.drawString(60, y_position, str(label))

            p.setFillColor(dark)
            p.drawRightString(
                width - 60,
                y_position,
                str(value)
            )

            y_position -= 25

        # Divider line
        p.setStrokeColor(gold)
        p.setLineWidth(1)

        p.line(
            50,
            y_position + 5,
            width - 50,
            y_position + 5
        )

        return y_position - 25

    # =========================================
    # RECEIPT INFO
    # =========================================
    receipt_info = [
        ("Receipt #", f"EW-{booking.id}"),
        ("Booking Status", booking.status_auto.title()),
        (
            "Created At",
            booking.created_at.strftime("%d %B %Y")
        ),
        ("Invoice Type", "Luxury Rental"),
    ]

    y = draw_section(
        "Receipt Information",
        receipt_info,
        y
    )

    # =========================================
    # CUSTOMER INFO
    # =========================================
    customer_info = [
        ("Customer", customer_name),
        ("Email", booking.user.email),
    ]

    y = draw_section(
        "Customer Details",
        customer_info,
        y
    )

    # =========================================
    # BOOKING INFO
    # =========================================
    booking_info = [
        ("Car", booking.car.name),
        ("Pickup Date", booking.pickup_date),
        ("Dropoff Date", booking.dropoff_date),
        ("Duration", f"{booking.duration} day(s)"),
        (
            "Pickup Location",
            booking.pickup_location or "Not specified"
        ),
        (
            "Dropoff Location",
            booking.dropoff_location or "Not specified"
        ),
        (
            "Driver Included",
            "Yes" if booking.with_driver else "No"
        ),
        ("Chauffeur", chauffeur_name),
    ]

    y = draw_section(
        "Booking Details",
        booking_info,
        y
    )

    # =========================================
    # TOTAL BOX
    # =========================================
    y -= 10

    p.setFillColor(dark)

    p.roundRect(
        50,
        y - 55,
        width - 100,
        75,
        12,
        fill=1,
        stroke=0
    )

    p.setFillColor(gold)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(70, y - 10, "TOTAL AMOUNT")

    p.setFont("Helvetica-Bold", 28)

    p.drawRightString(
        width - 70,
        y - 10,
        f"${booking.total_price:,.2f}"
    )

    # =========================================
    # FOOTER
    # =========================================
    p.setFillColor(gray)

    p.setFont("Helvetica-Oblique", 11)

    p.drawCentredString(
        width / 2,
        70,
        "Thank you for choosing EliteWheels."
    )

    p.drawCentredString(
        width / 2,
        50,
        "Experience Luxury. Drive Excellence."
    )

    p.showPage()
    p.save()

    return response

