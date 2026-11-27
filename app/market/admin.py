from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Message, Profile, Quote, SourcingRequest, StepRelease


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


# Invite an agent: add a user here and set Profile role to "Agent" with their Stripe test account.
admin.site.unregister(User)
admin.site.register(User, UserAdmin, inlines=[ProfileInline])


class QuoteInline(admin.TabularInline):
    model = Quote
    extra = 0


class StepInline(admin.TabularInline):
    model = StepRelease
    extra = 0


@admin.register(SourcingRequest)
class SourcingRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "item", "buyer", "status", "paid_cad", "created_at"]
    list_filter = ["status"]
    inlines = [QuoteInline, StepInline]


admin.site.register(Message)
