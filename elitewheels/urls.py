from django.contrib import admin
from django.urls import path
from myapp import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ================= CORE =================
    path('', views.home, name='home'),
    path('auth/', views.auth_view, name='auth'),

    # AUTH ACTIONS
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ================= DASHBOARD =================
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # ================= FLEET =================
    path('ourfleet/', views.fleet, name='fleet'),
    path('cardetails/<int:car_id>/', views.car_details, name='cardetails'),

    # ================= BOOKING =================
    path('book/<int:car_id>/', views.book_car, name='book_car'),
    path('confirmation/<int:booking_id>/', views.confirmation_view, name='confirmation'),

    path(
        'cancel-booking/<int:booking_id>/',
        views.cancel_booking,
        name='cancel_booking'
    ),
    path('car/<int:car_id>/review/', views.add_review, name='add_review'),

    # MUST EXIST (you were missing logic before)
    path(
        'booking/<int:booking_id>/',
        views.booking_detail,
        name='booking_detail'
    ),
    path('receipt/<int:booking_id>/',views.download_receipt,name='download_receipt'),    # ================= REVIEWS / FAVORITES =================
    path('review/<int:car_id>/', views.add_review, name='add_review'),
    path("favorite/<int:car_id>/", views.toggle_favorite, name="toggle_favorite"),    # ================= STATIC PAGES =================
    path('faq/', views.faq_view, name='faq'),
    path('contact/', views.contact_view, name='contact'),
    path('about/', views.about_view, name='about'),
    path('favorites/', views.dashboard_view, name='favorites'),

    # ================= PASSWORD RESET =================
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset_done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)