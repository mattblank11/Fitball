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
  average_list_of_dictionaries,
)
# Import methods from aws.py
from aws import (
  fetch_file_from_s3,
  post_file_to_s3,
)
# Import methods from app.py
from app import (
  user_goal_performance,
  fetch_avg_user_data,
  fetch_device_metrics,
)

user_info = fetch_user_data(
  config['whoop_username'],
  config['whoop_password'],
)

today = dt.datetime.today()
start_date = today - relativedelta(weeks = 1)
end_date = today

user_credentials = {
  'username': 'mb',
  'WHOOP': {
    'device_user_id': 9050,
    'device_access_token': 'pF6kI/CTnvNSKN/Vs/35vuTCeN+xlIXeTnWxWZFFqueVi06mfKCkj1Nj1YwMCF3H',
  }
}

goal_performance = user_goal_performance(
  user_credentials,  
)
