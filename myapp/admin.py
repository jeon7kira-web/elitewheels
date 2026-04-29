from django.contrib import admin
from .models import Car, Brand, Profile, Booking
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html


admin.site.register(Car)
admin.site.register(Brand)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "car", "pickup_date", "dropoff_date", "status_display")
    list_display_links = ("id", "user")
    list_filter = ("status", "car")
    search_fields = ("user__username", "car__name")

    def status_display(self, obj):
        status = obj.status_auto

        colors = {
            "confirmed": "goldenrod",
            "active": "green",
            "completed": "darkblue",
            "cancelled": "red",
        }

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(status, "black"),
            status.upper()
        )
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)  
