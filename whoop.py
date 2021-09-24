# Import packages
from settings import (
  requests,
  os,
  json,
  dt,
  relativedelta,
  pd,
  np,
  config,
)
# Import methods from compute.py
from compute import (
  format_date_as_string,
  format_date_str_as_datetime,
  convert_milliseconds_to_hours,
)

'''
Method: fetch_user_data

Summary: Fetches the WHOOP access token for a specific user
'''
def fetch_user_data(
    username,
    password,
):
    try:
        # Make a post request to fetch user info
        r = requests.post(
            'https://api-7.whoop.com/oauth/token',
            json={
                'grant_type': 'password',
                'issueRefresh': False,
                'password': password,
                'username': username,
            }
        )

        # Get request data as json
        r_json = r.json()

        # Parse user_info from r_json
        user_info = r_json['user']

        # Parse user_id from user_info
        user_id = user_info['id']

        # Parse access_token from r_json
        access_token = r_json['access_token']

        return {
            # 'user_info': user_info,
            'user_id': user_id,
            'access_token': access_token,
        }

    except KeyError:
        raise ValueError('Credentials could not be verified')

'''
Method: fetch_cycles_data

Summary: Fetches all the WHOOP health data for the specified user during a specified time period
'''
def fetch_cycles_data(
    user_id,
    access_token,
    start_date,
): 
    # Define cycles endpoint url
    cycles_url = f'https://api-7.whoop.com/users/{user_id}/cycles'

    # Define params for cycle data request using the specified start_date and end_date values
    today = dt.datetime.today()
    params = {
        'start': format_date_as_string(start_date),
        'end': format_date_as_string(today),
    }

    # Define headers for cycle data request
    headers = {
        'Authorization': f'bearer {access_token}'
    }

    # Make a post request to fetch cycles data
    cycles_data = requests.get(
        cycles_url,
        params = params,
        headers = headers,
    )

    # Get JSON from cycles_data
    cycles_data = cycles_data.json()

    return cycles_data

'''
Method: fetch_specific_whoop_data

Summary: Fetches strain, sleep, or recovery data from cycles
'''
def fetch_specific_whoop_data(
    cycles_data,
    whoop_data_type,
):
    # If the whoop_data_type is not one of the possible values,
    # return an error
    if (
        (whoop_data_type.lower() != 'strain')
        & (whoop_data_type.lower() != 'sleep')
        & (whoop_data_type.lower() != 'recovery')
    ):
        raise ValueError('whoop_data_type must be `strain`, `sleep`, or `recovery`')
    
    # Define an empty list of whoop_data
    whoop_data = []

    # Loop through each day in cycles_data
    for day in cycles_data:
        # Run the method for the correct data type
        if whoop_data_type.lower() == 'strain':
            whoop_data += format_strain_data(day)
        elif whoop_data_type.lower() == 'sleep':
            whoop_data += format_sleep_data(day)
        elif whoop_data_type.lower() == 'recovery':
            whoop_data += format_recovery_data(day)

    return whoop_data

'''
Method: format_sleep_data

Summary: Formats WHOOP sleep data
'''
def format_sleep_data(
    user_data,
):
    # Grab date from user_data and covert to a datetime object
    date_string = user_data['days'][0]
    date = format_date_str_as_datetime(date_string)

    # Get sleep_data from user_data
    sleep_data = user_data['sleep']

    # Define a list named formatted_sleep_data that will contain formatted
    # dictionaries of sleep_data
    formatted_sleep_data = []

    # Loop through each sleep cycle for the user
    for sleep in sleep_data['sleeps']:
        # Add formatted data to sleep_data_dict
        sleep_data_dict = {
            'date': date,
            'needBreakdown_baseline': convert_milliseconds_to_hours(sleep_data['needBreakdown']['baseline']),
            'needBreakdown_debt': convert_milliseconds_to_hours(sleep_data['needBreakdown']['debt']),
            'needBreakdown_naps': convert_milliseconds_to_hours(sleep_data['needBreakdown']['naps']),
            'needBreakdown_strain': convert_milliseconds_to_hours(sleep_data['needBreakdown']['strain']),
            'needBreakdown_total': convert_milliseconds_to_hours(sleep_data['needBreakdown']['total']),
            'qualityDuration': convert_milliseconds_to_hours(sleep_data['qualityDuration']),
            'score': sleep_data['score'],
            'cyclesCount': sleep['cyclesCount'],
            'disturbanceCount': sleep['disturbanceCount'],
            # 'id': sleep['id'],
            'inBedDuration': convert_milliseconds_to_hours(sleep['inBedDuration']),
            'isNap': sleep['isNap'],
            # 'latencyDuration': sleep['latencyDuration'],
            'lightSleepDuration': convert_milliseconds_to_hours(sleep['lightSleepDuration']),
            # 'noDataDuration': convert_milliseconds_to_hours(sleep['noDataDuration']),
            # 'qualityDuration': convert_milliseconds_to_hours(sleep['qualityDuration']),
            'remSleepDuration': convert_milliseconds_to_hours(sleep['remSleepDuration']),
            'respiratoryRate': sleep['respiratoryRate'],
            # 'responded': sleep['responded'],
            # 'score': sleep['score'],
            # 'sleepConsistency': sleep['sleepConsistency'],
            'slowWaveSleepDuration': convert_milliseconds_to_hours(sleep['slowWaveSleepDuration']),
            # 'source': sleep['source'],
            # 'state': sleep['state'],
            # 'surveyResponseId': sleep['surveyResponseId'],
            # 'timezoneOffset': sleep['timezoneOffset'],
            # 'wakeDuration': sleep['wakeDuration'],
        }
        
        # Append formatted_sleep_data to sleep_data_dict
        formatted_sleep_data.append(sleep_data_dict)

    return formatted_sleep_data

'''
Method: format_strain_data

Summary: Formats WHOOP strain data
'''
def format_strain_data(
    user_data,
):
    # Grab date from user_data and covert to a datetime object
    date_string = user_data['days'][0]
    date = format_date_str_as_datetime(date_string)

    # Get strain_data from user_data
    strain_data = user_data['strain']

    # Define a list named formatted_strain_data that will contain formatted
    # dictionaries of strain_data
    formatted_strain_data = []

    # Loop through each workout for the user
    for workout in strain_data['workouts']:
        # Add formatted data to strain_data_dict
        strain_data_dict = {
            'date': date,
            'averageHeartRate': strain_data['averageHeartRate'],
            'kilojoules': strain_data['kilojoules'],
            'maxHeartRate': strain_data['maxHeartRate'],
            'rawScore': strain_data['rawScore'],
            'score': strain_data['score'],
            # 'overallState': strain_data['state'],
            # 'altitudeChange': workout['altitudeChange'] or np.NaN,
            # 'altitudeGain': workout['altitudeGain'] or np.NaN,
            # 'averageHeartRate': workout['averageHeartRate'] or np.NaN,
            # 'cumulativeWorkoutStrain': workout['cumulativeWorkoutStrain'] or np.NaN,
            # 'distance': workout['distance'] or np.NaN,
            # 'gpsEnabled': workout['gpsEnabled'] or np.NaN,
            # 'id': workout['id'] or np.NaN,
            # 'kilojoules': workout['kilojoules'] or np.NaN,
            # 'maxHeartRate': workout['maxHeartRate'] or np.NaN,
            # 'rawScore': workout['rawScore'] or np.NaN,
            # 'responded': workout['responded'] or np.NaN,
            # 'score': workout['score'] or np.NaN,
            # 'source': workout['source'] or np.NaN,
            # 'sportId': workout['sportId'] or np.NaN,
            # 'state': workout['state'] or np.NaN,
            # 'surveyResponseId': workout['surveyResponseId'] or np.NaN,
            # 'timezoneOffset': workout['timezoneOffset'] or np.NaN,
            # 'zones': workout['zones'] or np.NaN,
        }

        # Append formatted_strain_data to strain_data_dict
        formatted_strain_data.append(strain_data_dict)

    return formatted_strain_data
'''
Method: format_recovery_data

Summary: Formats WHOOP recovery data
'''
def format_recovery_data(
    user_data,
):
    # Grab date from user_data and covert to a datetime object
    date_string = user_data['days'][0]
    date = format_date_str_as_datetime(date_string)

    # Get recovery_data from user_data
    recovery_data = user_data['recovery']

    # Define a list named formatted_recovery_data that will contain formatted
    # dictionaries of recovery_data
    formatted_recovery_data = []

    # Define a dictionary of recovery data
    recovery_data_dict = {
        'date': date,
        # 'blackoutUntil': recovery_data['blackoutUntil'],
        # 'calibrating': recovery_data['calibrating'],
        'heartRateVariabilityRmssd': recovery_data['heartRateVariabilityRmssd'],
        # 'id': recovery_data['id'],
        # 'responded': recovery_data['responded'],
        'restingHeartRate': recovery_data['restingHeartRate'],
        'score': recovery_data['score'],
        # 'state': recovery_data['state'],
        # 'surveyResponseId': recovery_data['surveyResponseId'],
        # 'timestamp': recovery_data['timestamp'],
    }

    # Append recovery_data_dict to formatted_recovery_data
    formatted_recovery_data.append(recovery_data_dict)

    return formatted_recovery_data
