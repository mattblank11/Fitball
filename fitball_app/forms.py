from django.forms import ModelForm, Widget
from django import forms
from .models import Device, Connected_Device, Goal, Discord, Competition
from django.contrib.auth.models import User

class connect_device_form(ModelForm):
    class Meta:
        model = Connected_Device
        fields = ['username', 'password']
        exclude = []
        widgets = {
            'username': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                    'placeholder': 'Username',
                }
            ),
            'password': forms.PasswordInput(
                attrs = {
                    'class': 'form-control',
                    'placeholder': 'Password',
                }
            ),
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

        self.fields["username"].label = ""
        self.fields["password"].label = ""
        if device_name.lower() == 'whoop':
            self.fields["username"].widget.attrs['placeholder'] = "Email"

class new_goal_form(ModelForm):
    class Meta:
        model = Goal
        fields = ['goal_category', 'clean_goal_metric', 'goal_value', 'goal_dollars']
        exclude = []
        widgets = {
            'goal_category': forms.Select(
                attrs = {
                    'class': 'form-control',
                    # 'placeholder': 'Category',
                }
            ),
            'clean_goal_metric': forms.Select(
                attrs = {
                    'class': 'form-control',
                    # 'placeholder': 'Metric',
                }
            ),
            'goal_value': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                    # 'placeholder': 'goal_value',
                }
            ),
            'goal_dollars': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                    # 'placeholder': 'goal_dollars',
                }
            ),
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
            'discord_id': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                    'placeholder': 'Discord ID (ex. Matt Blank #8486)',
                }
            ),
        }
        labels = {
            'discord_id': 'Discord ID',
        }
    def __init__(self, id, *args, **kwargs):
        super(discord_form, self).__init__(*args, **kwargs)
        self.fields["discord_id"].label = ""

class new_competition_form(ModelForm):
    class Meta:
        model = Competition
        fields = [
            'name',
            'device',
            'metric_category',
            'metric',
            'format',
            'goal_value',
            'dollars',
            'private',
        ]
        exclude = []
        widgets = {
            'name': forms.TextInput(
                attrs = {
                    'class': 'form-inline',
                    'placeholder': 'Fitballers',
                }
            ),
            'metric_category': forms.Select(
                attrs = {
                    'class': 'form-inline',
                    'placeholder': 'metric-category',
                }
            ),
            'metric': forms.Select(
                attrs = {
                    'class': 'form-inline',
                    'placeholder': 'metric',
                }
            ),
            'format': forms.Select(
                attrs = {
                    'class': 'form-inline',
                    'placeholder': 'format',
                }
            ),
            'goal_value': forms.TextInput(
                attrs = {
                    'class': 'form-inline',
                    'placeholder': 0,
                }
            ),
            'dollars': forms.TextInput(
                attrs = {
                    'class': 'form-inline',
                    'placeholder': 5,
                }
            ),
            'device': forms.Select(
                attrs = {
                    'class': 'form-inline',
                    'placeholder': 'device',
                }
            ),
            'private': forms.CheckboxInput(
                attrs = {
                    'class': 'form-check-input',
                }
            ),
        }
        labels = {
            'name': 'Group Name',
            'device': 'Device',
            'metric_category': 'Metric Category',
            'metric': 'Metric',
            'format': 'Competition Format',
            'goal_value': 'Value To Beat',
            'dollars': 'Dollars Per Day',
            'private': 'Private Competition',
        }
    def __init__(self, *args, **kwargs):
        super(new_competition_form, self).__init__(*args, **kwargs)
        default_device = Device.objects.get(device_name='WHOOP')
        self.fields['device'].initial = default_device.pk
        self.fields['device'].queryset = Device.objects.filter(
            active = True
        )
    