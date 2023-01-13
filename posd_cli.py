import boto3
import os
from pprint import pprint
import sys

ACCESS_KEY = os.environ['AWS_ACCESS_KEY_ID']
SECRET_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

BUCKET = "posd-approved-artifacts-bucket"
DYNAMO = "infra-stack-posdannouncementstableCACBA7F5-1OKB5F5DE93KX"


s3 = boto3.client('s3', region_name='us-east-1', aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)

dynamodb = boto3.client('dynamodb', region_name='us-east-1', aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)
                      
iam = boto3.client('iam', region_name='us-east-1', aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)


    
# List objects in a S3 bucket
def list_objects(bucket_name):
    response = s3.list_objects(Bucket=bucket_name)
    objects = [content['Key'] for content in response.get('Contents', [])]
    print(f"Artifact List in bucket: ")
    for object in objects:
        print(object)

# Upload file to S3 bucket
def upload_to_bucket(bucket_name, file_name):
    with open(file_name, 'rb') as data:
        s3.upload_fileobj(data, bucket_name, file_name)
    print(f"Artifact {file_name} has been uploaded.")

# Delete file from S3 bucket
def delete_from_bucket(bucket_name, file_name):
    s3.delete_object(Bucket=bucket_name, Key=file_name)
    print(f"{file_name} has been deleted from bucket.")

# List items from a Dynamo DB tbable
def list_items(table_name):
    response = dynamodb.scan(TableName=table_name)
    items = response['Items']
    for item in items:
        print(f"{item['date']['S']}: {item['announcement']['S']}")

# Insert an item into a DynamoDB table
def insert_item(table_name, announcement, date):
    item = {
        'announcement': {'S': announcement},
        'date': {'S': date}
    }
    dynamodb.put_item(TableName=table_name, Item=item)
    print("The announcement has been inserted into table.")

# Adding user to departmet
def add_user_to_department(user_name, department_name):
    iam.add_user_to_group(GroupName=department_name, UserName=user_name)
    print("User %s has been added to department %s." % (user_name, department_name))

# Deleting user from department
def delete_user_from_department(user_name,department_name):
    iam.remove_user_from_group(GroupName=department_name, UserName=user_name)
    print("User %s has been removed from department %s." % (user_name, department_name))


cmd = sys.argv[1]
if cmd == 'list_artifacts':
   
    try:
        list_objects(BUCKET)
    except:
        print("You do not have the right permissios to list artifacts.")
        print("Only the following departments are allowed to do this:")
        print("[ENGINEERING], [SUPPORT ENGINEERING]")

elif cmd == 'upload_artifact':
    file_name = sys.argv[2]
    try:
        upload_to_bucket(BUCKET, file_name)
    except:
        print("You do not have the right permissios to upload artifacts.")
        print("Only the following departments are allowed to do this:")
        print("[SUPPORT ENGINEERING]")

elif cmd == 'delete_artifact':
    file_name = sys.argv[2]
    try:
        delete_from_bucket(BUCKET, file_name)
    except:
        print("You do not have the right permissios to delete artifacts.")
        print("Only the following departments are allowed to do this:")
        print("[SUPPORT ENGINEERING]")

elif cmd == 'list_announcements':
    list_items(DYNAMO)

elif cmd == 'insert_announcement':
    announcement = sys.argv[2]
    date = sys.argv[3]
    try:
        insert_item(DYNAMO, announcement, date)
    except:
        print("You do not have the right permissios to add annuncements.")
        print("Only the following departments are allowed to do this:")
        print("[HUMAN RESOURCES]")

elif cmd == 'add_user_to_department':
    username = sys.argv[2]
    department = sys.argv[3]
    try:
        add_user_to_department(username, department)
    except:
        print("You do not have the permissios to add a user to a department.")
        print("Only an administrtor is able to perform this action")
    
elif cmd == 'delete_user_from_department':
    username = sys.argv[2]
    department = sys.argv[3]
    try:
        delete_user_from_department(username, department)
    except:
        print("You do not have the permissios to delete a user from a department.")
        print("Only an administrtor is able to perform this action")
elif cmd == 'help':
    print("The available commands are:\n")
    print("* list_artifacts - List the approved artifacts uploaded by the Support Engineering Team")
    print("\n* upload_artifact [artifact_name] - Upload a new approved artifact. This will give instant access to it for all Engineering department members")
    print("\n* delete_artifact [artifact_name] - Delete an existing approved artifact. This will instantly remove access to it for all Engineering department members")
    print("\n* list_announcements - List all public anouncements in the company")
    print("\n* insert_announcement [announcement] [date] - Publish a public announcement for all company members. This will send an email to all the subscribed employees")
    print("\n* add_user_to_department [user_name] [department_name] - Administrator only. Add a user to an existing department. Available department options: [HumanResourcesDepartment, EngineeringDepartment, SupportEngineeringDepartment]")
    print("\n* delete_user_from_department [user_name] [department_name] - Administrator only. Remove a user from an existing department. Available department options: [HumanResourcesDepartment, EngineeringDepartment, SupportEngineeringDepartment]")
else:
    print("Invalid command. Please use the help command to learn about the possible commands. The available commands are:")
    print("list_artifacts")
    print("upload_artifact [artifact_name]")
    print("delete_artifact [artifact_name]")
    print("list_announcements")
    print("insert_announcement [announcement] [date]")
    print("add_user_to_department [user_name] [department_name]")
    print("delete_user_from_department [user_name] [department_name]")



