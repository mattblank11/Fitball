from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from .models import Device, Connected_Device, Goal, Discord, Competition
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from .forms import connect_device_form, new_goal_form, discord_form, new_competition_form
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import urllib.parse
# Import methods from app
from app import (
    authenticate_user,
    fetch_device_metrics,
    fetch_all_device_metrics,
    user_goal_performance,
    fetch_user_performance,
    fetch_user_device_credentials,
    fetch_device_data,
    fetch_goal_data_from_device,
)
# Import methods from aws
from aws import (
  fetch_file_from_s3,
  post_file_to_s3,
)
# Import methods from discord_bot
from discord_bot import (
    fetch_user_id_from_username,
    fetch_dm_channel_id,
    send_message,
    create_new_channel,
)
# Import methods from views_methods
from views_methods import (
    check_device_credentials,
    check_discord_id,
    fetch_user_device,
    check_if_device_is_active,
    add_user_to_competition,
    join_competition_logic,
    determine_competition_winners,
    format_leaderboard_message,
)
# Import settings
from settings import (
  dt,
  relativedelta,
  json,
  os,
  np,
)

'''
Method: index

Summary: Index page
- If user has an account, log them in
- If user does not have an account, prompt them to connect a device
'''
def index(request):
    context = {}
    return render(request, 'app/index.html', context)

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
    id,
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
                device_credentials_work = check_device_credentials(
                    device,
                    form,
                    request,
                )

                # Render success page
                if device_credentials_work:
                    return HttpResponseRedirect(f'/new-goal/{device.id}')

            # If the user inputted invalid credentials, prompt the user to try again
            except ValueError:
                error_message = f"We couldn't connect to your {device.device_name}, please enter your information again."
                return render(
                    request,
                    'app/connect_device_form.html',
                    {
                        'form': form,
                        'id': id,
                        'device': device,
                        'device_logo': device_logo,
                        'error_message': error_message,
                    }
                )

    else:
        form = connect_device_form(id)
    
    return render(
        request,
        'app/connect_device_form.html',
        {
            'form': form,
            'id': id,
            'device': device,
            'device_logo': device_logo,
        }
    )

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
                goals_db = fetch_file_from_s3(os.environ['goals_db'])
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

                # If the user has already connected their Discord ID, render the success page
                has_discord_id = Discord.objects.filter(
                    user = request.user
                ).count() > 0
                if has_discord_id:
                    context = {'device': device, 'device_logo': device_logo}
                    return render(request, 'app/new_goal_success.html', context)
                # If the user has not already connected their Discord ID, prompt them to enter their Discord ID
                else:
                    return HttpResponseRedirect('/connect-discord')

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
Method: connect_discord_id

Summary: Connects the user's Discord ID to their account
'''
def connect_discord_id(
    request,
):
    form = discord_form()

    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    permission_classes = (IsAuthenticated,)

    if request.method == 'POST':
        form = discord_form(request.POST)

        # Check to ensure that the user inputted valid credentials, then run the following code
        if form.is_valid():
            try:
                # First, save the Discord ID to the Discord model
                username = check_discord_id(
                    form,
                    request,
                )

                # Try to send a message to the user. If the user is in the server, it will go through
                try:
                    # Get the user's id from their inputted Discord name. Their Discord name will be just their
                    # name without the discriminator
                    discord_name = (username).split(' #')[0]
                    user_id = fetch_user_id_from_username(
                        discord_name,
                    )

                    # Add the user's Discord ID to their Discord model
                    user_discord = Discord.objects.get(
                        user = request.user,
                    )
                    user_discord.discord_id = user_id
                    user_discord.save(update_fields=['discord_id'])

                    # Fetch the channel_id that lets FitBot chat with the user
                    channel_id = fetch_dm_channel_id(
                        user_id,
                    )

                    # Define a message to send to the user
                    message = f"""
            **👋 Hey <@{user_id}>, welcome to Fitball!**

If you need anything, I'm here to help! Just message me the following commands:
`!update` will pull your latest data and message back your performance against your goals
`!device` will send you the link to connect a new device (or reconnect your device)

Give it a shot - type `!update` below and hit enter 😃
            """
                    
                    send_message(
                        channel_id,
                        message,
                    )
    
                    # Render success page
                    context = {
                        'discord_id': user_id,
                    }
                    return render(request, 'app/discord_form_success.html', context)
                except IndexError:
                    raise ValueError('User not in Fitball Discord')

            # If the user inputted invalid credentials, prompt the user to try again
            except ValueError:
                error_message = f"We couldn't connect your Discord ID - follow the steps below and try again."
                return render(
                    request,
                    'app/discord_form.html',
                    {
                        'form': form,
                        'error_message': error_message,
                    }
                )

    else:
        form = discord_form()
  
    return render(
        request,
        'app/discord_form.html',
        {
            'form': form,
        },
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

'''
Method: update_user_performance_data

Summary: Pulls the latest user performance values for a specific user
'''
@require_POST
@csrf_exempt
def update_user_performance_data(
    request,
):
    # Get discord_username from message
    data = json.loads(request.body.decode('latin1'))
    discord_username = data['discord_username']

    # Get user from discord_username
    try:
        # Fetch the user from the discord_username if the user connected their Discord Username
        username = Discord.objects.get(discord_id = discord_username).user
        user = User.objects.get(username = username)
        # Specify the dates on which we want to update data: today and yesterday
        today = dt.datetime.now()
        yesterday = today - relativedelta(days = 1)
        two_days_ago = today - relativedelta(days = 2)
        dates = [two_days_ago, yesterday, today]

        # Update the user's data
        user_goal_performance(
            user.username,
            dates,
        )

        # Fetch the user's data as a list of dictionaries
        user_performance_data = fetch_user_performance(
            user.username,
            [yesterday, today],
        )

        return JsonResponse(user_performance_data, safe = False)
    except ObjectDoesNotExist:
        # Send message prompting user to connect device
        error_message = {
            'Error': 'We couldn\'t find a device or goal connected with your Discord Username. If you already connected a device, add your Discord Username [here](http://app.fitball.xyz/connect-discord/). If you haven\'t connected a device, type the !device command to do so'
        }
        return JsonResponse(error_message, safe = False)

    return JsonResponse(data, safe = False)

'''
Method: waitlist

Summary: adds a user to the waitlist for the specific device
'''
@require_POST
def waitlist(request):
    request_string = request.read().decode('utf-8')
    data = dict(urllib.parse.parse_qsl(request_string))

    # Fetch waitlist_db
    waitlist_db = fetch_file_from_s3(os.environ['waitlist_db'])
    
    # Append data to waitlist_db
    waitlist_db = waitlist_db.append(
                        {
                            'name': data['name'],
                            'email': data['email'],
                            'device': data['device'],
                        },
                        ignore_index=True,
                    ).drop_duplicates()

    # Post waitlist_db to s3
    post_file_to_s3(
        waitlist_db,
        'waitlist.csv',
    )

    return HttpResponse(
        json.dumps(data),
        content_type = 'application/json',
    )

'''
Method: new_competition

Summary: Allows the user to fill out a form to connect to the specified wearable device
'''
@login_required(login_url='/login/')
def new_competition(
    request,
):
    # Since we only want users to be able to create competitions, ensure that an
    # authenticated user created the competition
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    permission_classes = (IsAuthenticated,)
    
    form = new_competition_form()

    # Fetch the active devices
    active_devices = Device.objects.filter(
        active = True,
    ).values_list(
        'device_name',
        flat = True,
    )
    active_devices = list(active_devices)
    
    # Define a default device. We'll go with WHOOP for now
    default_device = 'WHOOP'

    # Fetch the categories and metrics for the active devices
    categories_and_metrics = fetch_all_device_metrics(
        active_devices,
    )

    if request.method == 'POST':
        form = new_competition_form(request.POST)

        if form.is_valid():
            # Get the content of the form
            form_data = form.save(commit = False)

            # Set the goal's start_date to right now
            form_data.start_date = timezone.now()

            # Get the device_metric_name from the clean_metric_name
            device_metrics = categories_and_metrics[form_data.device.device_name]['metrics']
            metric_name = [
                d['device_metric_name'] for d in device_metrics[form_data.metric_category] if d['clean_metric_name'] == form_data.metric
            ][0]

            # Set the clean_metric as form_data.metric
            form_data.clean_metric = form_data.metric

            # Create a Discord channel for the competition and save the discord_channel_id to the form
            discord_channel_id = create_new_channel(
                form_data.name,
            )
            form_data.discord_channel_id = discord_channel_id


            # Set the frequency to Daily
            form_data.frequency = 'Daily'
            
            # Send a message to the channel
            message = f"""
Hellooooooo party people!

Welcome to the **{form_data.name}** competition! Here's how it works:
Each **day**, you will put **${str(form_data.dollars)}** in a pool and compete with your group mates in a **{form_data.metric}** competition. If you **{'win' if form_data.format.lower() == 'winner take all' else 'beat the goal of ' + str(form_data.goal_value)}**, you will **{'get all the money in the pool' if form_data.format.lower() == 'winner take all' else 'split'}** the money in the pool.

If you want to see the leaderboard for the day, just ask by typing `!leaderboard`!

Have any questions? Ask Matt!
            """
            send_message(
                discord_channel_id,
                message,
            )

            # Save the form
            competition_id = form_data.id
            form_data.save()

            # Add the user to the competition
            form_data.users.add(request.user)

            # Add competition to competitions_db
            competitions_db = fetch_file_from_s3(os.environ['competitions_db'])
            new_row = [{
                'competition_id': competition_id,
                'name': form_data.name,
                'device_id': form_data.device.pk,
                'device': form_data.device.device_name,
                'metric_category': form_data.metric_category,
                'metric': metric_name,
                'clean_metric': form_data.metric,
                'format': form_data.format,
                'goal_value': form_data.goal_value,
                'dollars': form_data.dollars,
                'private': form_data.private,
                'start_date': form_data.start_date,
                'end_date': form_data.end_date,
                'frequency': 'Daily',
                'active': True,
                'discord_channel_id': discord_channel_id,
            }]
            competitions_db = competitions_db.append(
                new_row, ignore_index=True
            ).drop_duplicates(
                keep = 'last',
            )
            post_file_to_s3(
                competitions_db,
                'competitions.csv',
            )

            # Render the success page
            context = {
                'metric': form_data.metric,
                'device': form_data.device.device_name,
                'dollars': int(form_data.dollars),
                'format': f'beats the goal ({int(form_data.goal_value)})' if (form_data.format).lower() == 'beat the goal' else 'wins',
                'money_split': 'splits' if (form_data.format).lower() == 'beat the goal' else 'wins all the',
                'competition_id': Competition.objects.get(pk = form_data.id).pk,
            }
            
            return render(
                request,
                'app/new_competition_success.html',
                context,
            )

    else:
        form = new_competition_form()
  
    context = {
        'form': form,
        'categories_and_metrics': json.dumps(categories_and_metrics),
        'default_device': default_device,
    }
    return render(
        request,
        'app/new_competition_form.html',
        context,
    )

'''
Method: join_competition

Summary: Connects the user's Discord ID to their account
'''
def join_competition(
    request,
    id,
):
    authentication_classes = (
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    )
    permission_classes = (IsAuthenticated,)

    competition = Competition.objects.get(
        pk = id,
    )


    # When the user clicks the sign up button for the competition, run the following code
    if request.method == 'POST':
        # Fetch the submitted data
        request_string = request.read().decode('utf-8')
        data = dict(urllib.parse.parse_qsl(request_string))

        # # There are going to be a few different POST requests on this endpoint
        # If the action is 'join_competition', run the code to try and connect the user to the competition
        if data['action'] == 'join_competition':
            # First, run the code to connect the user's device
            connect_device(
                request,
                competition.device.pk,
            )
            # Then, run the rest of the join competition logic
            return join_competition_logic(
                request,
                request.user,
                competition,
            )
        
        # If the action is 'connect_device', run the code to check the user's device credentials
        elif data['action'] == 'connect_device':
            # First, run the code to connect the user's device
            connect_device(
                request,
                competition.device.pk,
            )
            # Then, run the rest of the join competition logic
            return join_competition_logic(
                request,
                request.user,
                competition,
            )

        # If the action is 'connect_discord', run the code to try and connect the user's Discord username
        elif data['action'] == 'connect_discord':
            # First, run the code to connect the user's Discord
            connect_discord_id(
                request,
            )
            # Then, run the rest of the join competition logic
            return join_competition_logic(
                request,
                request.user,
                competition,
            )

    context = {
        'name': competition.name,
        'device': competition.device.device_name,
        'metric': competition.metric,
        'dollars': int(competition.dollars),
        'format': f'beats the goal ({int(competition.goal_value)})' if (competition.format).lower() == 'beat the goal' else 'wins',
        'money_split': 'splits' if (competition.format).lower() == 'beat the goal' else 'wins all the',
        'competition_id': id,
    }
    return render(
        request,
        'app/join_competition.html',
        context,
    )

'''
Method: update_competition_performance

Summary: Update the performance data for each member in a specific competition

Steps:
(1) Fetch all the users in the competition
(2) Fetch the user's performance value for the competition metric
    -> If the user's device is disconnected, send a direct message to the user
       prompting them to reconnect their device 
(3) Populate a leaderboard with the results from the competition
(4) Message the leaderboard to the group
'''
@require_POST
@csrf_exempt
def update_competition_performance(
    request,
):
    # Fetch the request data
    data = json.loads(request.read().decode('utf-8'))
    # Format the date as a date
    date = dt.datetime.strptime(data['date'], '%Y-%m-%d')

    # First, retrieve the competition data from the Competition model
    discord_channel_id = data['discord_channel_id']
    # If the competition doesn't exist, return an error
    competition_exists = Competition.objects.filter(
        discord_channel_id = discord_channel_id,
    ).exists()
    if not competition_exists:
        return 'Competition does not exist'

    competition = Competition.objects.get(
        discord_channel_id = discord_channel_id,
    )

    competition_device = competition.device
    competition_device_name = competition_device.device_name

    # Fetch all the users in the competition
    competition_users = competition.users.all()

    # Define an empty list of user data that we'll populate as we loop through each user
    user_data = []

    # Loop through each user in competition_users
    for user in competition_users:
        # Fetch the user's device credentials
        user_device = Connected_Device.objects.get(
            user = user,
            device = competition_device,
        )
        user_device_credentials = fetch_user_device_credentials(
            user_device,
            competition_device_name,
        )
        # Check to ensure the user's device is active
        user_device_is_active = check_if_device_is_active(
            user_device,
            competition_device_name,
        )
        if user_device_is_active:
            # Fetch the user's device data
            user_device_data = fetch_device_data(
                competition_device_name,
                user_device_credentials,
                dt.datetime.today(),
            )
            # Fetch the user's performance value for the competition
            competition_metrics = {
                'goal_category': competition.metric_category,
                'device_goal_metric': competition.metric,
            }
            user_performance_value = fetch_goal_data_from_device(
                competition_device_name,
                user_device_data,
                competition_metrics,
                dt.datetime.today(),
            )
            # Append user data to user_data
            user_data.append({
                'date': data['date'],
                'user_id': user.pk,
                'device_id': competition.device.pk,
                'competition_id': competition.pk,
                'user': user.username,
                'discord_id': user.discord.discord_id,
                'device': competition.device.device_name,
                'metric_category': competition.metric_category,
                'clean_metric': competition.clean_metric,
                'metric': competition.metric,
                'goal_value': competition.goal_value,
                'dollars': competition.dollars,
                'user_value': user_performance_value,
            })
        else:
            # Send a direct message to the user prompting them to reconnect their device
            reconnect_message = f"Hey <@{user.discord.discord_id}>! Please reconnect your {competition.device.device_name} to keep participating in the {competition.name} competition. You can do so through [this link](http://app.fitball.xyz/connect-device/{competition.device.pk}) 💪"
            send_message(
                user.discord.discord_id,
                reconnect_message,
            )

            # Append user data to user_data
            user_data.append({
                'date': data['date'],
                'user_id': user.pk,
                'device_id': competition.device.pk,
                'competition_id': competition.pk,
                'user': user.username,
                'discord_id': user.discord.discord_id,
                'device': competition.device.device_name,
                'metric_category': competition.metric_category,
                'clean_metric': competition.clean_metric,
                'metric': competition.metric,
                'goal_value': competition.goal_value,
                'dollars': competition.dollars,
                'user_value': np.nan,
            })

    # Create a dictionary of lists of dictionaries separating users into winners,
    # losers, and people whose devices were disconnected
    leaderboard_dict = determine_competition_winners(
        user_data,
        competition,
    )
    
    # Format the leaderboard_dict into a message
    leaderboard_message = format_leaderboard_message(
        leaderboard_dict,
        competition,
    )

    # Send the leaderboard message to the group
    send_message(
        competition.discord_channel_id,
        leaderboard_message,
    )
    
    return HttpResponse(
        json.dumps(data),
        content_type = 'application/json',
    )