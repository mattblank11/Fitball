from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'fitball'
urlpatterns = [
    path('', views.devices, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name="app/login.html"), name='login'),
    path('devices/', views.devices, name='devices'),
    path('connect-device/<str:id>/', views.connect_device, name='connect-device'),
    path('new-goal/<str:id>/', views.new_goal, name='new-goal'),
    path('connect-discord/', views.connect_discord_id, name='connect-discord'),
    path('new-competition/', views.new_competition, name='new-competition'),
    path('api/update-performance/', views.update_all_user_performance_data, name='api/update-performance'),
    path('api/update-user-performance/', views.update_user_performance_data, name='api/update-user-performance'),
    path('api/waitlist/', views.waitlist, name='api/waitlist'),
]