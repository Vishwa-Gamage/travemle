from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from planner.views import (
    DestinationListView,
    LoginView,
    MeView,
    RegisterView,
    TravelPlanView,
    TripHistoryView,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Auth endpoints
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/auth/me/', MeView.as_view(), name='me'),

    # Planner endpoints
    path('api/plan-trip/', TravelPlanView.as_view(), name='plan-trip'),
    path('api/destinations/', DestinationListView.as_view(), name='destinations'),
    path('api/trip-history/', TripHistoryView.as_view(), name='trip-history'),
    path('api/trip-history/<int:pk>/', TripHistoryView.as_view(), name='trip-delete'),
]
