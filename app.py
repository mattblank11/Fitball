# Import packages
from settings import (
  requests,
  os,
  json,
  dt,
  relativedelta,
  pd,
  np,
  s3_fs,
  s3_boto,
  s3_bucket,
  s3_bucket_path,
  StringIO,
)
# Import methods from whoop.py
from whoop import (
  fetch_user_data,
  fetch_cycles_data,
  fetch_specific_whoop_data,
)
# Import methods from compute.py
from compute import (
  format_date_as_string,
  beat_goal,
  fetch_user_value_on_date,
  average_list_of_dictionaries,
)
# Import methods from aws.py
from aws import (
  fetch_file_from_s3,
  post_file_to_s3,
  fetch_active_user_goals,
)

'''
Method: authenticate_user

Summary: Authenticates the user usingtheir login credentials
'''
def authenticate_user(
    device,
    user,
):
    # WHOOP
    if device.lower() == 'whoop':
        user = fetch_user_data(
            user['username'],
            user['password'],
        )

        return user

'''
Method: user_goal_performance

Summary: Runs the code to update user performance and
determine if a user hit their goals over a list of dates
'''
def user_goal_performance(
    user,
    dates,
):
    # Fetch the data from the goals db for the user
    user_goals = fetch_active_user_goals(user)

    # Fetch the data from the performance db for the user
    performance_db = fetch_file_from_s3(os.environ['performance_db'])
    performance_db['date'] = pd.to_datetime(performance_db['date'])

    # Fetch the connected_devices_db
    connected_devices_db = fetch_file_from_s3(os.environ['connected_devices_db'])

    # Identify the devices we need to collect data from to update user data
    # Since a user may have multiple goals for each active device
    user_devices = list(set([device['device'] for device in user_goals]))

    # Loop through each device that we need to update data from
    for device in user_devices:
        # Fetch user's device_credentials
        device_credentials = fetch_user_device_credentials(
            user,
            device,
            connected_devices_db,
        )

        # Update the performance for the device in the loop
        performance_db = update_user_device_performance(
            device,
            device_credentials,
            user_goals,
            performance_db,
            dates,
        )

    # Post performance_db to s3
    post_file_to_s3(
        performance_db,
        'performance.csv'
    )

'''
Method: update_user_device_performance

Summary: Updates the user's performance data for a specific device
'''
def update_user_device_performance(
    device,
    device_credentials,
    user_goals,
    performance_db,
    dates,
):
    # Get the performance_db from the parameters so we can update it
    updated_performance_db = performance_db.copy()

    # Filter user_goals to get goals for this device
    device_goals = [goal for goal in user_goals if goal['device'] == device]

    # Loop through each date in dates
    for date in dates:
        # Fetch the user's latest data for the specified device
        device_data = fetch_device_data(
            device,
            device_credentials,
            date,
        )
        # Loop through each of the user's goals for this device
        for goal in device_goals:

            # The date may return a date in the future since this is working
            # in the cloud. If that's the case, skip this date.
            try:
                user_value = fetch_goal_data_from_device(
                    device,
                    device_data,
                    goal,
                    date,
                )

                # Define how we'll check for a unique row
                unique_columns = [
                    'date',
                    'user',
                    'device',
                    'goal_category',
                    'device_goal_metric',
                ]

                # Check if user had already hit this goal on the specified date. If so,
                # we won't trigger a payment

                # Check if user beat goal
                user_beat_goal = beat_goal(
                    user_value,
                    goal['goal_value'],
                    '>',
                )

                # Add or update row in performance_db
                new_data = {
                    'date': date.date(),
                    'user_id': goal['user_id'],
                    'device_id': goal['device_id'],
                    'goal_id': goal['goal_id'],
                    'user': goal['user'],
                    'device': goal['device'],
                    'goal_category': goal['goal_category'],
                    'clean_goal_metric': goal['clean_goal_metric'],
                    'device_goal_metric': goal['device_goal_metric'],
                    'goal_value': goal['goal_value'],
                    'goal_dollars': goal['goal_dollars'],
                    'user_value': user_value,
                    'user_beat_goal': user_beat_goal,
                }

                updated_performance_db = updated_performance_db.append(
                    new_data,
                    ignore_index = True
                ).drop_duplicates(
                    subset = unique_columns,
                    keep = 'last',
                )
                
            except IndexError:
                continue

    return updated_performance_db 

'''
Method: fetch_user_device_credentials

Summary: Fetches the user's credentials for the specified device
'''
def fetch_user_device_credentials(
    user,
    device,
    connected_devices_db,
):
    # WHOOP
    if device.lower() == 'whoop':
        user_device_row = connected_devices_db[
            (connected_devices_db['user'].str.lower() == user.lower())
            & (connected_devices_db['device'].str.lower() == device.lower())
        ]

        device_user_id = user_device_row['device_user_id'].values[0]
        device_access_token = user_device_row['device_access_token'].values[0]

        return {
            'device_user_id': device_user_id,
            'device_access_token': device_access_token,
        }


'''
Method: fetch_device_data

Summary: Fetches the user's data for the specified device
'''
def fetch_device_data(
    device,
    device_credentials,
    start_date,
):
    # WHOOP
    if device.lower() == 'whoop':
        return fetch_cycles_data(
            device_credentials['device_user_id'],
            device_credentials['device_access_token'],
            start_date,
        )

'''
Method: fetch_goal_data_from_device

Summary: Gets the user's device data for the specific goal
'''
def fetch_goal_data_from_device(
    device,
    device_data,
    goal_data,
    date,
):
    # WHOOP
    if device.lower() == 'whoop':
        whoop_data = fetch_specific_whoop_data(
            device_data,
            goal_data['goal_category'],
        )

        return fetch_user_value_on_date(
            whoop_data,
            goal_data['device_goal_metric'],
            date,
        )

'''
Method: fetch_device_metrics

Summary: Returns a list of possible goal metrics for the specified device
'''
def fetch_device_metrics(
    device,
    device_credentials,
):
    # Fetch the user's data for each metric
    user_data = fetch_avg_user_data(
        device,
        device_credentials,
    )

    # Fetch the data from the device_metrics_db
    device_metrics = fetch_file_from_s3(os.environ['device_metrics_db'])

    # Filter device metrics on the specified device
    device_metrics = device_metrics[device_metrics['device'].str.lower() == device.lower()]

    # Filter device metrics to only include active metrics
    device_metrics = device_metrics[device_metrics['active'] == 1]

    # Fetch all the categories from device_metrics
    categories = list(set([category for category in device_metrics['category']]))

    # Create a dictionary containing lists of metrics for each category, along with the user's values for that category
    metrics = {}
    for category in categories:
        device_category_metrics = list(set([m for m in device_metrics[device_metrics['category'] == category]['device_metric_name']]))
        metrics[category] = []
        # Loop through each metric in category_metrics to add data to metrics
        for metric in device_category_metrics:
            clean_metric_name = device_metrics.loc[
                (
                    (device_metrics['category'] == category)
                    &  (device_metrics['device_metric_name'] == metric)
                ),
                'clean_metric_name'
            ].values[0]
            metrics[category].append({
                'clean_metric_name': clean_metric_name,
                'device_metric_name': metric,
                'avg': user_data[category.lower()][metric]['average'] or 0,
                'list': user_data[category.lower()][metric]['list'] or 0,
            })

    # Return the metrics as a list
    return {
        'categories': categories,
        'metrics': metrics,
        'all_data': device_metrics,
    }

'''
Method: fetch_avg_user_data

Summary: Gets the user's average device data values. This data will be used to suggest a goal
'''
def fetch_avg_user_data(
    device,
    device_credentials,
):
    # WHOOP
    if device.lower() == 'whoop':
        # Default start_date to 7 days ago
        start_date = dt.datetime.today() - relativedelta(days = 7)
        device_data = fetch_device_data(
            device,
            device_credentials,
            start_date,
        )
        strain_data = fetch_specific_whoop_data(
            device_data,
            'strain',
        )
        recovery_data = fetch_specific_whoop_data(
            device_data,
            'recovery',
        )
        sleep_data = fetch_specific_whoop_data(
            device_data,
            'sleep',
        )
        return {
            'strain': average_list_of_dictionaries(strain_data),
            'recovery': average_list_of_dictionaries(recovery_data),
            'sleep': average_list_of_dictionaries(sleep_data),
        }

'''
Method: fetch_user_performance

Summary: Gets the user's data from the performance_db on
'''
def fetch_user_performance(
    user,
    dates,
):
    # Fetch the performance_db
    performance_db = fetch_file_from_s3(os.environ['performance_db'])
    performance_db['date'] = (pd.to_datetime(performance_db['date'])).dt.date

    # Filter the performance_db to just the data for the specified user
    performance_db = performance_db[performance_db['user'] == user]

    # Define an array of performance data to return for the user
    user_performance_data = []

    # Loop through each date
    for date in dates:
        # Filter performance_db to just the data on the specified date
        performance_on_date = performance_db[performance_db['date'] == date.date()]
        # Loop through each performance on that date
        for index, row in performance_on_date.iterrows():
            user_performance_data.append({
                'date': date,
                'device': row['device'],
                'goal_category': row['goal_category'],
                'clean_goal_metric': row['clean_goal_metric'],
                'goal_value': row['goal_value'],
                'goal_dollars': row['goal_dollars'],
                'user_value': row['user_value'],
                'user_beat_goal': row['user_beat_goal'],
            })

    # Return user_performance_data
    return user_performance_data