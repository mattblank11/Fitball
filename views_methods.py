# Import Django settings
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
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
    np,
)

'''
Method: check_device_credentials

Summary: Checks whether the user submitted working device credentials
'''
def check_device_credentials(
    device,
    form,
    request,
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

    # Log the user in
    login(
        request,
        user,
    )

    return True

'''
Method: check_discord_id

Summary: Checks whether the user entered a Discord ID that exists in the Fitball Discord
'''
def check_discord_id(
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
        existing_discord_id.discord_username = form_data.discord_username
        existing_discord_id.save()

    except ObjectDoesNotExist:
        form_data.save()
    
    return form_data.discord_username

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

    # If the device is not active, device_data will return a dictionary with a
    # key of 'message' and a value of 'Unauthorized'. If it doesn't, return 'True'
    if isinstance(device_data, dict):
        if 'message' in device_data:
            if device_data['message'] == 'Unauthorized':
                return False
    return True

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
    # If the user has never signed up for Fitball, they're going to need to create a user profile
    # (by connecting a device) before they do so
    if not user.is_authenticated:
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

'''
Method: determine_win_threshold

Summary: Returns the cutoff for whether or not a user won the competition
- Competition format is `winner take all`: max user_value
- Competition format is `beat the goal`: competition.goal_value
'''
def determine_win_threshold(
    user_data,
    competition,
):
    # Get the user_values as a list
    user_values = [d['user_value'] for d in user_data if d['user_value'] is not np.nan]

    # If the competition format is `beat the goal`, return competition.goal_value
    if competition.format.lower() == 'beat the goal':
        return competition.goal_value

    # If the competition format is `winner take all`, return the max user value
    elif competition.format.lower() == 'winner take all':
        return max(user_values)

'''
Method: determine_user_competition_status

Summary: Returns 1 of the 3 values for a user:
(1) 'winner' if the user's user_value exceeds the win_threshold
(2) 'loser' if the user's user_value is less than the win_thrshold
(3) 'disconnected' if the user's user_vale is nan
'''
def determine_user_competition_status(
    user_value,
    win_threshold,
):
    # If the user's user_value is nan, return 'disconnected'
    if user_value is np.nan:
        return 'disconnected'
    elif user_value >= win_threshold:
        return 'winner'
    elif user_value < win_threshold:
        return 'loser'

'''
Method: sort_list_of_dictionaries

Summary: Returns a sorted list of dictionaries
'''
def sort_list_of_dictionaries(
    list,
    sorting_variable,
):
    # Return the list sorted by the sorting variable
    return sorted(
        list,
        key = lambda d: d[sorting_variable],
        reverse = True,
    )

'''
Method: determine_competition_winners

Summary: Determines the winner(s) of a competition given user and competition data

Output: A dictionary of lists of dictionaries, with 3 dictionary values:
(1) winners
(2) losers
(3) disconnected
'''
def determine_competition_winners(
    user_data,
    competition,
):
    # Define a dictionary of lists of dictionaries we'll return
    result = {
        'winner': [],
        'loser': [],
        'disconnected': [],
    }

    # Determine the threshold for whether or not a user won
    win_threshold = determine_win_threshold(
        user_data,
        competition,
    )

    # Loop through each user in user_data
    for user in user_data:
        # Add a 'status' variable that returns 'winner' if the
        # user's user_value exceeds the win_threshold, 'loser' if it is lower,
        # and 'disconnected' if the user_value is nan
        user['status'] = determine_user_competition_status(
            user['user_value'],
            win_threshold,
        )

        # Add the user to result
        result[user['status']].append(user)
    
    # Sort the winner, loser, and disconnected lists within result
    result = {
        'winner': sort_list_of_dictionaries(
            result['winner'],
            'user_value',
        ),
        'loser': sort_list_of_dictionaries(
            result['loser'],
            'user_value',
        ),
        'disconnected': result['disconnected'],
    }

    return result

'''
Method: determine_winner_payouts

Summary: Calculates the payment per winner by dividing the total pool by the number of winners
'''
def determine_winner_payouts(
    competition,
    number_of_winners,
):
    # Calculate the total pool
    total_pool = competition.dollars * len(competition.users.all())
    
    # If there are no winners, return the total pool
    if number_of_winners == 0:
        if (total_pool).is_integer():
            return int(total_pool)
        else:
            return round(total_pool, 2)
    
    # If there's at least 1 winner, return the total pool (dollars per user * # users)
    # by the number of winners. If there's only 1 winner, this will just return the
    # total pool
    winners_share_of_pool = total_pool / number_of_winners
    if (winners_share_of_pool).is_integer():
        return int(winners_share_of_pool)
    else:
        return round(winners_share_of_pool, 2)

'''
Method: format_headline_message

Summary: Returns a headline message for the competition
'''
def format_headline_message(
    leaderboard_data,
    number_of_winners,
    winner_payment,
):
    # If there are no winners, return a message saying that no one won
    if number_of_winners == 0:
        return f"Nobody won the ${winner_payment} pool today 🥺 step it up tomorrow!"

    # Determine if the headline should say 'winner' (if number_of_winners == 1) or 'winners'
    winner_text = 'winner'
    if number_of_winners == 1:
        pass
    elif number_of_winners > 1:
        winner_text += 's'

    # Loop through each winner in leaderboard data to incldue them in the headline
    winners = ' and '.join([winner['discord_id'] for winner in leaderboard_data['winner']])
    
    return f"Congrats to {winners} for winning ${winner_of_payment} on {date}! Here are the rest of the results:"

'''
Method: format_leaderboard_message

Summary: Formats the leaderboard data into a message we'll send to the group
'''
def format_leaderboard_message(
    leaderboard_data,
    competition,
):
    # Fetch the number of winners
    number_of_winners = len(leaderboard_data['winner'])

    # Fetch the payment for each winner
    winner_payment = determine_winner_payouts(
        competition,
        number_of_winners,
    )

    # Create a headline message to include
    headline = format_headline_message(
        leaderboard_data,
        number_of_winners,
        winner_payment,
    )

    # Format the winner section
    # If there are no winners, return 'No winners today 🥺 step it up tomorrow!'
    winner_message = ''
    if len(leaderboard_data['winner']) > 0:
        winner_message = f"""

**Winner / {competition.clean_metric} Value**"""
 
    for winner in leaderboard_data['winner']:
        winner_message += f"<@{winner['discord_id']}> / {winner['user_value']}"
    
    # Format the loser section
    win_threshold = determine_win_threshold(
        leaderboard_data['winner'],
        competition,
    )
    # If there are no losers, return 'No losers in this crew today 🤑'
    loser_message = ''
    if len(leaderboard_data['loser']) > 0:
        loser_message = f"""

**Runner Up / {competition.clean_metric} Value / # Behind Winners**"""
    else:
        loser_message = f"""
        
No losers in this group today 🤑"""

    for loser in leaderboard_data['loser']:
        loser_message += f"<@{loser['discord_id']}> / {loser['user_value']} / {win_threshold - loser['user_value']}"
    
    # Format the disconnected section
    # If there are no losers, return 'Need to reconnect their {competition.device.device_name}: none 😃'
    disconnected_message = ''
    if len(leaderboard_data['disconnected']) > 0:
        reconnect_users = ' and '.join([f"<@{winner['discord_id']}>" for winner in leaderboard_data['disconnected']])
        print(reconnect_users)
        disconnected_message = f"""

{reconnect_users} {'need' if len(leaderboard_data['disconnected']) > 1 else 'needs'} to reconnect their {competition.device.device_name}"""
    
    # Combine all the parts of the message
    message = headline + winner_message + loser_message + disconnected_message

    return message
