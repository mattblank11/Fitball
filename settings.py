# Import environment variables
from dotenv import dotenv_values
config = dotenv_values('.env')
# Import packages
import requests
import os
import json
import datetime as dt
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
# S3
import boto3
from s3fs.core import S3FileSystem
s3_bucket = config['s3_bucket']
s3_bucket_path = 's3://' + s3_bucket
s3_fs = S3FileSystem(anon=False)
s3_boto = boto3.resource('s3')
from io import StringIO
