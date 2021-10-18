# Import Django settings
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from fitball_app.models import Device, Connected_Device, Goal, Discord, Competition
from fitball_app.forms import connect_device_form, new_goal_form, discord_form, new_competition_form
# Import methods from app
from app import (
    authenticate_user,
    fetch_device_metrics,
    fetch_device_data,
    fetch_all_device_metrics,
    user_goal_performance,
    fetch_user_performance,
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
# Import settings
from settings import (
    dt,
    relativedelta,
    json,
    os,
)

'''
Method: check_device_credentials

Summary: Checks whether the user submitted working device credentials
'''
def check_device_credentials(
    User,
    Connected_Device,
    device,
    form,
):
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
    connected_devices_db = fetch_file_from_s3(os.environ['connected_devices_db'])

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
            'device_access_token'
        ] = device_auth['access_token']
        connected_devices_db.loc[
            (
                (connected_devices_db['user'] == user.username)
                & (connected_devices_db['device'] == device.device_name)
            ),
            'device_user_id'
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

    return True

'''
Method: check_discord_id

Summary: Checks whether the user entered a Discord ID that exists in the Fitball Discord
'''
def check_discord_id(
    Discord,
    form,
    request,
):
    # Get the content of the form
    form_data = form.save(commit = False)
    
    # Set the discord id's user to the authenticated user
    form_data.user = request.user
    
    # If the user has already enterred their Discord ID, replace the value. Otherwise,
    # add the data as a new entry to the database
    try:
        existing_discord_id = Discord.objects.get(
            user = request.user
        )
        existing_discord_id.discord_id = form_data.discord_id
        existing_discord_id.save()

    except ObjectDoesNotExist:
        form_data.save()
    
    return form_data.discord_id

'''
Method: fetch_user_device

Summary: Fetches a specific device that the user has connected
'''
def fetch_user_device(
    user,
    device,
):
    return Connected_Device.objects.get(
        user = user,
        device = device,
    )

'''
Method: check_if_user_has_device

Summary: Checks whether the user entered a Discord ID that exists in the Fitball Discord
'''
def check_if_user_has_device(
    user,
    device,
):
    return Connected_Device.objects.filter(
        user = user,
        device = device,
    ).exists()

'''
Method: check_if_device_is_active

Summary: Checks whether the user entered a Discord ID that exists in the Fitball Discord
'''
def check_if_device_is_active(
    user_device,
    device_name,
):
    # Check if the user's credentials are active by fetching data for the specified device
    user_credentials = {
        'device_user_id': user_device.device_user_id,
        'device_access_token': user_device.device_access_token,
    }
    device_data = fetch_device_data(
        device_name,
        user_credentials,
        dt.datetime.today(),
    )

    # If fetch_device_data returns data, return True. Otherwise, raise an error
    if device_data:
        return True
    else:
        return False

'''
Method: check_if_user_connected_discord

Summary: Checks if a user has a connected Discord ID
'''
def check_if_user_connected_discord(
    user,
):
    return Discord.objects.filter(
        user = user,
    ).exists()

'''
Method: check_if_user_is_in_competition

Summary: Checks if a user is already in a competition
'''
def check_if_user_is_in_competition(
    user,
    competition,
):
    return competition.users.filter(
        pk = user.pk,
    ).exists()

'''
Method: add_user_to_competition

Summary: Adds a user to a specific competition
'''
def add_user_to_competition(
    user,
    competition,
):
    # Add user to the competition model
    competition.users.add(user)

    # Send a message to the competition Discord group welcoming the user
    discord_name = (user.discord.discord_id).split(' #')[0]
    discord_user_id = fetch_user_id_from_username(
        discord_name,
    )
    message = f'Welcome to the {competition.name} competition, <@{discord_user_id}>!'
    send_message(
        competition.discord_channel_id,
        message,
    )

'''
Method: join_competition_logic

Summary: Manages the logic for adding a user to a competition
'''
def join_competition_logic(
    request,
    user,
    competition,
):
    # If the user is already in the competition, redirect them to the page with the
    # join link and prompt them to add a friend
    user_already_in_competition = check_if_user_is_in_competition(
        user,
        competition,
    )
    if user_already_in_competition:
        context = {
            'metric': competition.metric,
            'device': competition.device.device_name,
            'dollars': int(competition.dollars),
            'format': f'beats the goal ({int(competition.goal_value)})' if (competition.format).lower() == 'beat the goal' else 'wins',
            'money_split': 'splits' if (competition.format).lower() == 'beat the goal' else 'wins all the',
            'competition_id': competition.pk,
            'already_joined_header': f"You're already in the {competition.name} competition!\nCopy the link below to invite a friend 😃",
        }
            
        return render(
            request,
            'app/new_competition_success.html',
            context,
        )

    # Users need to do 2 things before they are added to a competition:
    # (1) Connect a device that's compatible with the competition.
    #     This device must be actively connected and pulling data.
    # (2) Connect their Discord ID

    # Check if the user already has a device connected:
    user_connected_device = check_if_user_has_device(
        user,
        competition.device,
    )
    # If the user has connected their device, check if the device is actively pulling data
    if user_connected_device:
        # Fetch the user's device
        user_device = fetch_user_device(
            user,
            competition.device,
        )
        # Check that the user's connected device is actively pulling data
        user_device_is_active = check_if_device_is_active(
            user_device,
            user_device.device.device_name,
        )
        # If the user's device is actively pulling data, check if they have connected their Discord
        if user_device_is_active:
            # Check if the user has already connected their Discord
            user_connected_discord = check_if_user_connected_discord(
                user,
            )
            # If the user has already connected Discord, sign them up for the competition
            if user_connected_discord:
                add_user_to_competition(
                    user,
                    competition,
                )

                context = {
                    'metric': competition.metric,
                    'device': competition.device.device_name,
                    'dollars': int(competition.dollars),
                    'format': f'beats the goal ({int(competition.goal_value)})' if (competition.format).lower() == 'beat the goal' else 'wins',
                    'money_split': 'splits' if (competition.format).lower() == 'beat the goal' else 'wins all the',
                    'competition_id': competition.pk,
                    'already_joined_header': f"You're officially in the {competition.name} competition!\nCopy the link below to invite a friend 😃",
                }
                
                return render(
                    request,
                    'app/new_competition_success.html',
                    context,
                )
            # If the user has not connected their Discord, prompt them to connect their Discord
            else:
                context = {
                    'form': discord_form(),
                    'success_message': f"Connect your Discord to join the {competition.name} competition!",
                }
                return render(
                    request,
                    'app/discord_form.html',
                    context,
                )
            # If the user has not connected Discord, prompt them to connect their Discord
        # If the user's device is not actively pulling data, prompt them to reconnect their device
        else:
            form = connect_device_form(competition.device.pk)
            sign_up_message = f"Reconnect your {competition.device.device_name} to join the {competition.name} competition!"
            return render(
                request,
                'app/connect_device_form.html',
                {
                    'form': form,
                    'id': competition.device.pk,
                    'device': competition.device,
                    'device_logo': competition.device.logo.url,
                    'success_message': sign_up_message,
                }
            )
        
    # If the user has not connected their device, prompt them to connect the device
    else:
        form = connect_device_form(competition.device.pk)
        sign_up_message = f"Connect your {competition.device.device_name} to join the {competition.name} competition!"
        return render(
            request,
            'app/connect_device_form.html',
            {
                'form': form,
                'id': competition.device.pk,
                'device': competition.device,
                'device_logo': competition.device.logo.url,
                'success_message': sign_up_message,
            }
        )
