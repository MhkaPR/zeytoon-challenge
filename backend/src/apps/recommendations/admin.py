from django.contrib import admin

from apps.recommendations.models import InterestProfile, InterestSignal


@admin.register(InterestProfile)
class InterestProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "visitor_id", "signal_count", "last_signal_at")
    search_fields = ("user__phone_number", "visitor_id")


@admin.register(InterestSignal)
class InterestSignalAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "kind", "created_at")
    list_filter = ("kind",)
