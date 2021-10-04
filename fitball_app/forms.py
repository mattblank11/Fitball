from django.forms import ModelForm, Widget
from django import forms
from .models import Device, Connected_Device, Goal, Discord
from django.contrib.auth.models import User

class connect_device_form(ModelForm):
    class Meta:
        model = Connected_Device
        fields = ['username', 'password']
        exclude = []
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Username',
            'password': 'Password',
        }
    def __init__(self, id, *args, **kwargs):
        super(connect_device_form, self).__init__(*args, **kwargs)
        device = Device.objects.get(pk=id)
        device_id = device.id
        device_name = device.device_name

        if device_name.lower() == 'whoop':
            self.fields["username"].label = "Email"

class new_goal_form(ModelForm):
    class Meta:
        model = Goal
        fields = ['goal_category', 'clean_goal_metric', 'goal_value', 'goal_dollars']
        exclude = []
        widgets = {
            'goal_category': forms.Select(attrs={'class': 'form-control'}),
            'clean_goal_metric': forms.Select(attrs={'class': 'form-control'}),
            'goal_value': forms.TextInput(attrs={'class': 'form-control'}),
            'goal_dollars': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'goal_category': 'Category',
            'clean_goal_metric': 'Metric',
            'goal_value': 'Goal Value',
            'goal_dollars': 'Dollars',
        }
    def __init__(self, id, *args, **kwargs):
        super(new_goal_form, self).__init__(*args, **kwargs)
        device = Device.objects.get(pk=id).id

class discord_form(ModelForm):
    class Meta:
        model = Discord
        fields = ['discord_id']
        exclude = []
        widgets = {
            'discord_id': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'discord_id': 'Discord ID',
        }
    def __init__(self, id, *args, **kwargs):
        super(discord_form, self).__init__(*args, **kwargs)