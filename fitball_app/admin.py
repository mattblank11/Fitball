from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Device, Connected_Device, Goal, Discord

admin.site.register(Device)
admin.site.register(Connected_Device)
admin.site.register(Goal)
admin.site.register(Discord)

class ConnectedDeviceInline(admin.StackedInline):
    model = Connected_Device
    can_delete = False
    verbose_name_plural = 'device'

class GoalInline(admin.StackedInline):
    model = Goal
    can_delete = False
    verbose_name_plural = 'goal'

class DiscordInline(admin.StackedInline):
    model = Discord
    can_delete = False
    verbose_name_plural = 'discord'

class UserAdmin(BaseUserAdmin):
    inlines = (ConnectedDeviceInline, GoalInline, DiscordInline)

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
