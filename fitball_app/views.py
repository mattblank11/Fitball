from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import Device, Connected_Device, Goal
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from .forms import connect_device_form, new_goal_form
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
# Import methods from app
from app import (
    authenticate_user,
    fetch_device_metrics,
    user_goal_performance,
)
# Import methods from aws
from aws import (
  fetch_file_from_s3,
  post_file_to_s3,
)
# Import settings
from settings import (
  dt,
  relativedelta,
  json,
)

'''
Method: index

Summary: Index page
- If user has an account, log them in
- If user does not have an account, prompt them to connect a device
'''
def index(request):
    return HttpResponse('Hello world!')

'''
Method: devices

Summary: Prompts the user to connect a wearable device
'''
def devices(request):
    devices = Device.objects.order_by('display_number')
    context = {'devices': devices}
    return render(request, 'app/devices.html', context)

'''
Method: connect_device

Summary: Allows the user to fill out a form to connect to the specified wearable device
'''
def connect_device(
    request,
    id
):
    form = connect_device_form(id)
    devices = Device.objects.order_by('display_number')
    device = Device.objects.get(pk=id)
    device_logo = device.logo.url

    if request.method == 'POST':
        form = connect_device_form(id, request.POST)

        if form.is_valid():
            # Check to ensure that the user inputted valid credentials, then run the following code
            try:
                # Get the content of the form
                form_data = form.save(commit = False)

                # Check if the user's credentials work
                user_credentials = {
                    'username': form_data.username,
                    'password': form_data.password,
                }

                device_auth = authenticate_user(
                    device.device_name,
                    user_credentials
                )

                # Check if the user has already connected a device. If not, create a new user
                new_user = User.objects.filter(username = form_data.username).count() == 0
                if new_user:
                    User.objects.create_user(username = form_data.username, password = form_data.password)
                user = User.objects.get(username = form_data.username)

                # Fetch connected_devices_db so we can update it
                connected_devices_db = fetch_file_from_s3(config['connected_devices_db'])

                # If the user is not new, and they have already connected to this device, then update
                # the data. Otherwise, create a new row
                try:
                    existing_device = Connected_Device.objects.get(
                        user = user,
                        device = device,
                    )
                    existing_device.device_access_token = device_auth['access_token']
                    existing_device.device_user_id = device_auth['user_id']
                    existing_device.save()

                    # Update values in connected_devices_db
                    connected_devices_db.loc[
                        (
                            (connected_devices_db['user'] == user.username)
                            & (connected_devices_db['device'] == device.device_name)
                        ),
                        'access_token'
                    ] = device_auth['access_token']
                    connected_devices_db.loc[
                        (
                            (connected_devices_db['user'] == user.username)
                            & (connected_devices_db['device'] == device.device_name)
                        ),
                        'user_id'
                    ] = device_auth['user_id']

                except ObjectDoesNotExist:
                    # Set values for form_data
                    form_data.user = user
                    form_data.username = ''
                    form_data.password = ''
                    form_data.device_access_token = device_auth['access_token']
                    form_data.device_user_id = device_auth['user_id']
                    form_data.device = device
                    form_data.save()

                    # Append row to connected_devices_db
                    new_row = [{
                        'user_id': user.id,
                        'device_id': device.id,
                        'user': user.username,
                        'device': device.device_name,
                        'device_access_token': device_auth['access_token'],
                        'device_user_id': device_auth['user_id'],
                    }]
                    connected_devices_db = connected_devices_db.append(
                        new_row, ignore_index=True
                    ).drop_duplicates(
                        subset = ['user', 'device'],
                        keep = 'last',
                    )

                # Save connected_devices_db to S3
                post_file_to_s3(
                    connected_devices_db,
                    'connected_devices.csv',
                )

                # Render success page
                context = {'device': device, 'device_logo': device_logo}
                return render(request, 'app/connect_device_success.html', context)

            # If the user inputted invalid credentials, prompt the user to try again
            except ValueError:
                error_message = f"We couldn't connect to your {device.device_name}, please enter your information again."
                return render(request, 'app/connect_device_form.html', {'form': form, 'id': id, 'device': device, 'device_logo': device_logo, 'error_message': error_message})

    else:
        form = connect_device_form(id)
  
    return render(request, 'app/connect_device_form.html', {'form': form, 'id': id, 'device': device, 'device_logo': device_logo})

'''
Method: new_goal

Summary: Allows the user to add a goal for a specific device
'''
def new_goal(
    request,
    id
):
    form = new_goal_form(id)
    devices = Device.objects.order_by('display_number')
    device = Device.objects.get(pk=id)
    device_logo = device.logo.url

    # Fetch the categories and metrics for the specified device
    connected_device = Connected_Device.objects.get(
        user = request.user,
        device = device,
    )
    user_credentials = {
        'device_user_id': connected_device.device_user_id,
        'device_access_token': connected_device.device_access_token,
    }
    categories_and_metrics = fetch_device_metrics(
        device.device_name,
        user_credentials,   
    )
    device_categories = categories_and_metrics['categories']
    device_metrics = categories_and_metrics['metrics']

    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    permission_classes = (IsAuthenticated,)

    if request.method == 'POST':
        form = new_goal_form(id, request.POST)

        if form.is_valid():
            # Check to ensure that the user inputted valid credentials, then run the following code
            try:
                # Get the content of the form
                form_data = form.save(commit = False)

                # Set the goal's start_date to right now
                form_data.start_date = timezone.now()

                # Set the goal's active state to active
                form_data.active = True

                # Set the goal's device to device
                form_data.device = device

                # Set the goal's user to the authenticated user
                form_data.user = request.user

                # Get the device_metric_name from the clean_metric_name
                device_metric_name = [
                    d['device_metric_name'] for d in device_metrics[form_data.goal_category] if d['clean_metric_name'] == form_data.clean_goal_metric
                ][0]
                form_data.device_goal_metric = device_metric_name

                # If the user is not new, and they have already connected to this device, then update
                # the data. Otherwise, create a new row
                goal_id = 0
                try:
                    existing_goal = Goal.objects.get(
                        user = request.user,
                        device = device,
                        goal_category = form_data.goal_category,
                        device_goal_metric = device_metric_name,
                    )
                    existing_goal.goal_value = form_data.goal_value
                    existing_goal.goal_dollars = form_data.goal_dollars
                    goal_id = existing_goal.id
                    existing_goal.save()

                except ObjectDoesNotExist:
                    goal_id = form_data.id
                    form_data.save()

                # Add goal to goals_db
                goals_db = fetch_file_from_s3(config['goals_db'])
                new_row = [{
                    'user_id': request.user.id,
                    'device_id': device.id,
                    'goal_id': goal_id,
                    'user': request.user.username,
                    'device': device.device_name,
                    'goal_category': form_data.goal_category,
                    'clean_goal_metric': form_data.clean_goal_metric,
                    'device_goal_metric': device_metric_name,
                    'goal_value': form_data.goal_value,
                    'goal_dollars': form_data.goal_dollars,
                    'active': form_data.active,
                    'start_date': form_data.start_date,
                    'end_date': form_data.end_date,
                }]
                goals_db = goals_db.append(
                    new_row, ignore_index=True
                ).drop_duplicates(
                    subset = ['user', 'device', 'goal_category', 'device_goal_metric'],
                    keep = 'last',
                )
                post_file_to_s3(
                    goals_db,
                    'goals.csv',
                )

                # Render success page
                context = {'device': device, 'device_logo': device_logo}
                return render(request, 'app/new_goal_success.html', context)

            # If the user inputted invalid credentials, prompt the user to try again
            except ValueError:
                error_message = f"We couldn't connect to your {device.device_name}, please enter your information again."
                return render(request, 'app/new_goal_form.html', {'form': form, 'id': id, 'device': device, 'device_logo': device_logo, 'error_message': error_message})

    else:
        form = new_goal_form(id)
  
    return render(
        request,
        'app/new_goal_form.html',
        {
            'form': form,
            'id': id,
            'device': device,
            'device_logo': device_logo,
            'device_categories': json.dumps(device_categories),
            'device_metrics': json.dumps(device_metrics),
        }
    )

'''
Method: update_all_user_performance_data

Summary: Pulls the latest user performance values for each user
'''
@require_POST
@csrf_exempt
def update_all_user_performance_data(
    request,
):
    # Fetch the data for all users
    users = User.objects.all()
    
    # Loop through each user
    for user in users:
        # Try to run the code for each user, but add an IndexError exception in case that user
        # hasn't yet added any goals or connected any devices
        # try:
            # Specify the dates on which we want to update data: today and yesterday
            today = dt.datetime.now()
            yesterday = today - relativedelta(days = 1)
            two_days_ago = today - relativedelta(days = 2)
            dates = [two_days_ago, yesterday, today]

            user_goal_performance(
                user.username,
                dates,
            )
        # except IndexError:
        #     continue

    response = {
        'Mission': 'Accomplished',
    }
    return JsonResponse(response, safe = False)
    