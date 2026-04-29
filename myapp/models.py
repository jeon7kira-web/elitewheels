from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from django.utils import timezone


# ---------------- PROFILE ----------------
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    license = models.FileField(upload_to='licenses/')

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


# ---------------- BRAND ----------------
class Brand(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# ---------------- CAR ----------------
class Car(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)
    car_type = models.CharField(max_length=50)
    transmission = models.CharField(max_length=20)
    passengers = models.IntegerField()
    fuel_type = models.CharField(max_length=20)
    image = models.ImageField(upload_to='cars/')
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    year = models.IntegerField(null=True, blank=True)
    mileage = models.IntegerField(null=True, blank=True)
    air_conditioning = models.BooleanField(default=True)
    bluetooth = models.BooleanField(default=True)
    gps = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# ---------------- CAR IMAGES ----------------
class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='cars/gallery/')


class Chauffeur(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    license_number = models.CharField(max_length=50)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name
# ---------------- BOOKING ----------------
class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)

    pickup_date = models.DateField()
    dropoff_date = models.DateField()

    with_driver = models.BooleanField(default=False)

    chauffeur = models.ForeignKey(
    Chauffeur,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    @property
    def duration(self):
        return (self.dropoff_date - self.pickup_date).days
    # 🔥 COMPLETION CHECK
    @property
    def status_auto(self):
        today = timezone.now().date()

        if self.status == "cancelled":
            return "cancelled"
        if today < self.pickup_date:
            return "confirmed"
        if self.pickup_date <= today <= self.dropoff_date:
            return "active"
        return "completed"

    # 🔒 VALIDATION
    def clean(self):
        if self.pickup_date >= self.dropoff_date:
            raise ValidationError("Dropoff date must be after pickup date.")

        overlapping = Booking.objects.filter(
            car=self.car,
            status__in=['pending', 'confirmed']
        ).filter(
            Q(pickup_date__lt=self.dropoff_date) &
            Q(dropoff_date__gt=self.pickup_date)
        )

        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)

        if overlapping.exists():
            raise ValidationError("This car is already booked for these dates.")

    # 💰 AUTO PRICE
    def save(self, *args, **kwargs):
        self.full_clean()
        days = (self.dropoff_date - self.pickup_date).days
        if days > 0:
            self.total_price = days * self.car.price_per_day
            if self.with_driver:
                self.total_price += days * 50  # +50 MAD/day for driver
        super().save(*args, **kwargs)

