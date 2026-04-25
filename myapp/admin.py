from django.contrib import admin
from .models import Car, Brand, Profile
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

admin.site.register(Car)
admin.site.register(Brand)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)