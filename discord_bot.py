# Import settings
from settings import (
    json,
    os,
    requests,
)
# Get Discord environment variables
guild_id = os.environ['discord_server_id']
discord_token = os.environ['discord_token']
competitions_category_id = os.environ['competitions_category_id']
base_url = 'https://discord.com/api'

'''
Method: fetch_user_id_from_username

Summary: Returns a user's user_id given their Discord username
'''
def fetch_user_id_from_username(
    discord_name,
):
    data = {
        "query": [discord_name],
    }
    r = requests.get(
        base_url + f'/guilds/{guild_id}/members/search',
        headers = {
            'authorization': f"Bot {discord_token}",
        },
        params = data,
    )
    user_id = r.json()[0]['user']['id']
    return user_id

'''
Method: fetch_dm_channel_id

Summary: Fetches the channel id for a dm between FitBot and a specific user
'''
def fetch_dm_channel_id(
    user_id,
):
    data = {
        'recipient_id': user_id,
    }
    r = requests.post(
        base_url + '/users/@me/channels',
        headers = {
            'authorization': f"Bot {discord_token}",
            'Content-Type': 'application/json',
        },
        json = data,
    )
    channel_id = r.json()['id']
    return channel_id

'''
Method: send_message_to_user

Summary: Sends a direct message to a specific user
'''
def send_message(
    channel_id,
    message,
):
    data = {
        'content': message,
    }
    r = requests.post(
        base_url + f'/channels/{channel_id}/messages',
        headers = {
            'authorization': f"Bot {discord_token}",
            'Content-Type': 'application/json',
        },
        json = data,
    )

'''
Method: create_new_channel

Summary: Creates a new channel
'''
def create_new_channel(
    channel_name,
):
    # Create the channel
    data = {
        'name': channel_name,
        'type': 0, # 0 represents a text channel
        'parent_id': competitions_category_id,
        'permission_overwrites': [
            {
                'id': guild_id,
                'allow': '523328', # These permissions basically allow group members to chat with each other
                'deny': '1024', # Disallows members from viewing channel
            },
        ],
    }
    r = requests.post(
        base_url + f'/guilds/{guild_id}/channels',
        headers = {
            'authorization': f"Bot {discord_token}",
            'Content-Type': 'application/json',
        },
        json = data,
    )
    
    discord_channel_id = r.json()['id']
    
    return discord_channel_id