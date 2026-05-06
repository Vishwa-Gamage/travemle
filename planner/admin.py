from django.contrib import admin
from .models import Destination, TripPlan


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'category', 'is_featured', 'created_at']
    list_filter = ['category', 'country', 'is_featured']
    search_fields = ['name', 'description', 'country']
    list_editable = ['is_featured']
    ordering = ['-is_featured', 'name']


@admin.register(TripPlan)
class TripPlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'origin', 'destination_city', 'destination_country',
                    'start_date', 'end_date', 'budget', 'travel_mode', 'created_at']
    list_filter = ['travel_mode', 'destination_country', 'created_at']
    search_fields = ['user__username', 'origin', 'destination_city']
    readonly_fields = ['plan_json', 'map_url', 'weather_summary', 'created_at']
    date_hierarchy = 'created_at'
