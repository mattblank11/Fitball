# Import packages
from settings import (
    dt,
)

'''
Method: format_date_as_string

Summary: Takes a date object and converts it to a string that
is compatible with the WHOOP API
'''
def format_date_as_string(
    date
):
    # This method only works if the date variable is a datetime
    # value. If not, return an error
    if type(date) is not dt.datetime:
        raise ValueError('Specified date is not a datetime object')

    # Define the WHOOP compatible date string format
    whoop_date_string_format = '%Y-%m-%dT%H:%m:%SZ'

    return date.strftime(whoop_date_string_format)

'''
Method: format_date_str_as_datetime

Summary: Takes a date string and converts it to a datetime object
'''
def format_date_str_as_datetime(
    date_string
):
    return dt.datetime.strptime(date_string, '%Y-%m-%d')

'''
Method: convert_milliseconds_to_hours

Summary: Converts milliseconds to hours
'''
def convert_milliseconds_to_hours(
    milliseconds
):
    return milliseconds / (60 * 60 * 1000)

'''
Method: fetch_user_value_on_date

Summary: Fetches a value for a specified metric on a specified date
'''
def fetch_user_value_on_date(
    user_data,
    metric,
    date,
):
    # Get the data for the specified date
    data_on_date = [data for data in user_data if (
        (data['date'].year == date.year)
        & (data['date'].month == date.month)
        & (data['date'].day == date.day)
    )][0]

    # Get the value for the specified metric
    metric_value = data_on_date[metric]

    return metric_value

'''
Method: beat_goal

Summary: Determines if the user beat a specified goal
'''
def beat_goal(
    metric_value,
    goal_value,
    direction,
):
    # Determine if user beat goal
    if direction == '>':
        return metric_value >= goal_value
    elif direction == '<':
        return metric_value <= goal_value

'''
Method: average_list_of_dictionaries

Summary: Returns a dictionary with the average value for each key across a list of dictionaries
'''
def average_list_of_dictionaries(
    list_of_dictionaries,
):
    # Define a dictionary to return
    return_dictionary = {}

    # Get all the keys that we'll return in return_dictionary
    keys = list_of_dictionaries[0].keys()

    for key in keys:
        if key != 'date':
            return_dictionary[key] = {
                'average': sum(d.get(key, 0) for d in list_of_dictionaries) / len(list_of_dictionaries),
                'list': [d.get(key, 0) for d in list_of_dictionaries],
            }
    
    return return_dictionary
