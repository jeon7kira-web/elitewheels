from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    license = models.FileField(upload_to='licenses/')


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
class Brand(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Car(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)
    car_type = models.CharField(max_length=50)
    transmission = models.CharField(max_length=20)
    passengers = models.IntegerField()
    fuel_type = models.CharField(max_length=20)
    image = models.ImageField(upload_to='cars/')
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    pickup_date = models.DateField()
    dropoff_date = models.DateField()

    def clean(self):
        if self.dropoff_date <= self.pickup_date:
            raise ValidationError("Dropoff must be after pickup")

        overlapping = Booking.objects.filter(
            car=self.car,
            pickup_date__lt=self.dropoff_date,
            dropoff_date__gt=self.pickup_date
        )

        if overlapping.exists():
            raise ValidationError("This car is already booked for these dates")