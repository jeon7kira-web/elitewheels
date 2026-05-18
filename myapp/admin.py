from django.utils.html import format_html
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Car
from .models import Booking, Profile


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "car",
        "pickup_date",
        "dropoff_date",
        "status_display",
        "total_price",
    )

    list_display_links = ("id", "user")
    list_filter = ("status", "car", "pickup_date")
    search_fields = ("user__username", "car__name")
    ordering = ("-created_at",)

    readonly_fields = ("total_price",)

    def status_display(self, obj):
        status = obj.status_auto

        colors = {
            "confirmed": "#f1c40f",
            "active": "#2ecc71",
            "completed": "#3498db",
            "cancelled": "#e74c3c",
            "pending": "#95a5a6",
        }

        return format_html(
            '<span style="color:{}; font-weight:700;">{}</span>',
            colors.get(status, "black"),
            status.upper()
        )

    status_display.short_description = "Status"

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand",
        "price_per_day",
        "discount_percent",
        "discount_start",
        "discount_end",
        "status",
        "discount_status"
    )
   
    list_filter = ("status", "brand", "discount_percent")
    search_fields = ("name", "brand__name")

    fieldsets = (
        ("Car Info", {
            "fields": ("name", "brand", "car_type", "transmission", "fuel_type", "passengers")
        }),
        ("Pricing", {
            "fields": ("price_per_day", "discount_percent")
        }),
        ("Discount Timer (NEW 🔥)", {
            "fields": ("discount_start", "discount_end")
        }),
        ("Media", {
            "fields": ("image", "features")
        }),
        ("Status", {
            "fields": ("status",)
        }),
        
    )
    def discount_status(self, obj):
        if obj.is_discount_active:
            return format_html(
        '<span style="padding:3px 8px;border-radius:12px;background:{};color:white;font-size:11px;">{}</span>',
        "#2ecc71" if obj.is_discount_active else "#e74c3c",
        "ACTIVE" if obj.is_discount_active else "OFF"
)
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)  
