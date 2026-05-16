from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q,Avg, Count
from django.utils import timezone



# PROFILE
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=20)
    license = models.FileField(upload_to='licenses/')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


# BRAND
class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True)

    logo = models.ImageField(
        upload_to='brands/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.name


# FEATURE
class Feature(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# LOCATION
class Location(models.Model):
    city = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return f"{self.city} - {self.address}"


# CAR
class Car(models.Model):

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('rented', 'Rented'),
        ('maintenance', 'Maintenance'),
    ]

    name = models.CharField(max_length=100)

    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='cars'
    )

    car_type = models.CharField(max_length=50)
    transmission = models.CharField(max_length=20)
    passengers = models.IntegerField()
    fuel_type = models.CharField(max_length=20)

    image = models.ImageField(upload_to='cars/')

    price_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    description = models.TextField(blank=True)

    year = models.IntegerField(null=True, blank=True)
    mileage = models.IntegerField(null=True, blank=True)

    features = models.ManyToManyField(Feature, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    @property
    def average_rating(self):
        return self.reviews.aggregate(avg=Avg("rating"))["avg"] or 0
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def available(self):
        today = timezone.now().date()

        overlapping = Booking.objects.filter(
            car=self,
            dropoff_date__gte=today,
            status__in=['pending', 'confirmed', 'active']
        )

        return not overlapping.exists()

    def __str__(self):
        return f"{self.brand.name} {self.name}"


# CAR IMAGES
class CarImage(models.Model):
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(upload_to='cars/gallery/')

    def __str__(self):
        return f"{self.car.name} Image"


# CHAUFFEUR
class Chauffeur(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    license_number = models.CharField(max_length=50)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# BOOKING
class Booking(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="bookings")
    pickup_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pickup_bookings'
    )

    dropoff_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dropoff_bookings'
    )

    pickup_date = models.DateField()
    dropoff_date = models.DateField()

    with_driver = models.BooleanField(default=False)

    chauffeur = models.ForeignKey(
        Chauffeur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # duration
    @property
    def duration(self):
        return max(1, (self.dropoff_date - self.pickup_date).days)

    # auto status
    @property
    def status_auto(self):
        today = timezone.now().date()

        if self.status == "cancelled":
            return "cancelled"

        if today < self.pickup_date:
            return "confirmed"

        if self.pickup_date <= today <= self.dropoff_date:
            return "active"

        if today > self.dropoff_date:
            return "completed"

        return "pending"

    def clean(self):
        if self.pickup_date >= self.dropoff_date:
            raise ValidationError("Dropoff date must be after pickup date.")

        overlapping = Booking.objects.filter(
            car=self.car,
            status__in=['pending', 'confirmed', 'active']
        ).filter(
            Q(pickup_date__lt=self.dropoff_date) &
            Q(dropoff_date__gt=self.pickup_date)
        )

        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)

        if overlapping.exists():
            raise ValidationError("This car is already booked for these dates.")

    def save(self, *args, **kwargs):
        self.full_clean()

        days = max(1, (self.dropoff_date - self.pickup_date).days)
        self.total_price = days * self.car.price_per_day

        if self.with_driver:
            self.total_price += days * 50

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.car.name}"


# FAVORITE
class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites"
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="favorited_by"
    )
# PAYMENT
class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.booking.user.username}"


# PROMO CODE
class PromoCode(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.IntegerField()
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.code


# NOTIFICATION
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# MAINTENANCE
class Maintenance(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='maintenances')
    title = models.CharField(max_length=100)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.car.name} - {self.title}"


# REVIEW
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.car.name}"