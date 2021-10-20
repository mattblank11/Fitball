from django.db import models
from django.contrib.auth.models import User

class Device(models.Model):
    device_name = models.CharField(max_length = 200)
    display_number = models.IntegerField(default = 0)
    logo = models.ImageField(blank = True, null = True, upload_to = "media/")
    active = models.BooleanField(default = False)
    def __str__(self):
        return self.device_name

class Connected_Device(models.Model):
    username = models.CharField(max_length = 200, default = '')
    password = models.CharField(max_length = 200, default = '')
    device_user_id = models.CharField(max_length = 200)
    device_access_token = models.CharField(max_length = 200)
    device = models.ForeignKey(Device, on_delete = models.CASCADE, null = True)
    user = models.ForeignKey(User, default = None, blank = True, null = True, on_delete = models.CASCADE)
    def __str__(self):
        return f'{self.user.username} // {self.device.device_name}'

class Goal(models.Model):
    user = models.ForeignKey(User, default = None, blank = True, null = True, on_delete = models.CASCADE)
    device = models.ForeignKey(Device, on_delete = models.CASCADE, null = True)
    goal_category = models.CharField(max_length = 200)
    clean_goal_metric = models.CharField(max_length = 200)
    device_goal_metric = models.CharField(max_length = 200)
    goal_value = models.FloatField(max_length = 200)
    goal_dollars = models.FloatField(max_length = 200)
    active = models.BooleanField(default = False)
    start_date = models.DateTimeField(blank = True, null = True)
    end_date = models.DateTimeField(blank = True, null = True)
    def __str__(self):
        return f'{self.user.username} // {self.goal_category} // {self.clean_goal_metric} // {self.goal_value}'

class Discord(models.Model):
    user = models.OneToOneField(User, default = None, null = True, on_delete = models.CASCADE)
    discord_username = models.CharField(max_length = 200)
    discord_id = models.CharField(max_length = 200)
    def __str__(self):
        return self.discord_username

class Competition(models.Model):
    name = models.CharField(max_length = 200)
    metric = models.CharField(max_length = 200)
    clean_metric = models.CharField(max_length = 200)
    metric_category = models.CharField(max_length = 200)
    format = models.CharField(max_length = 200)
    frequency = models.CharField(max_length = 200)
    goal_value = models.FloatField(default = 0)
    dollars = models.FloatField(default = 0)
    active = models.BooleanField(default = True)
    private = models.BooleanField(default = True)
    start_date = models.DateTimeField(blank = True, null = True)
    end_date = models.DateTimeField(blank = True, null = True)
    discord_channel_id = models.CharField(max_length = 200)
    users = models.ManyToManyField(User)
    device = models.ForeignKey(Device, on_delete = models.CASCADE, blank = True, null = True)
    def __str__(self):
        return f'{self.name} // {self.device} // {self.metric_category} // {self.metric} // {self.format}'
