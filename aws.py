from settings import (
    pd,
    json,
    s3_fs,
    s3_boto,
    s3_bucket,
    s3_bucket_path,
    StringIO,
    os,
)

'''
Method: fetch_file_from_s3

Summary: Fetches a file from s3 and returns it as a dataframe
'''
def fetch_file_from_s3(
    file_name,
):
    # Fetch file from s3
    df = pd.read_csv(
        s3_fs.open(
            s3_bucket_path + '/' + file_name,
        )
    )

    return df

'''
Method: post_file_to_s3

Summary: Updates a file in S3
'''
def post_file_to_s3(
    df,
    file_name,
):
    csv_buffer = StringIO()
    df.to_csv(
        csv_buffer,
        index=False
    )
    s3_boto.Bucket(
        s3_bucket
    ).put_object(
        Key = file_name,
        Body=csv_buffer.getvalue()
    )

'''
Method: fetch_user_goals

Summary: Fetches goals for a specific user and returns goals as json
'''
def fetch_active_user_goals(
    username,
):
    # Fetch all goals from db
    user_goals = fetch_file_from_s3(os.environ['goals_db'])

    # Filter goals for specified user and ensure goals are still active
    user_goals = user_goals[
        (user_goals['user'] == username)
        & (user_goals['active'] == True)
    ]
    
    # Format user_goals as json
    user_goals_json = user_goals.to_json(orient = 'records')

    return json.loads(user_goals_json)