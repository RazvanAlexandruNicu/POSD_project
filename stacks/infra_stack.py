from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_lambda_event_sources as dynamo_event
)


class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create resources used in the company
        # S3 bucket for storing approved artifacts
        # This bucket will be used by Support Engineers to upload approved artifacts
        # Engineers working on our projects will have read-only access to the artifacts bucket to download the approved software
        approved_artifacts_bucket = s3.Bucket(
            self, 
            "ApprovedArtifactsBucket", 
            bucket_name = "posd-approved-artifacts-bucket"
            )
        
        # DynamoDB table in which HR people will post announcements, that can be retrieved by all the employees
        announcements_table = dynamodb.Table(
            self, 
            "posd-announcements-table",
            partition_key=dynamodb.Attribute(name="announcement", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="date", type=dynamodb.AttributeType.STRING),
            read_capacity=5, 
            write_capacity=5,
            stream=dynamodb.StreamViewType.NEW_IMAGE
            )
        
        # Create a new Lambda function that is triggered when a new announcement is published and prints the announcement
        sns_publisher_lambda = _lambda.Function(
            self, 
            'MyLambdaFunction',
            runtime=_lambda.Runtime.PYTHON_3_8,
            code=_lambda.Code.from_inline(
"""
import boto3

def handler(event, context):
    # Create an SES client
    ses = boto3.client('ses')

    event = event['Records'][0]
    if event['eventName'] == "INSERT":
        date = event['dynamodb']['Keys']['date']['S']
        message = event['dynamodb']['Keys']['announcement']['S']
        print(f"Date: {date}. Announcement: {message}")

        # Define the email message
        message = {
            'Subject': {
                'Data': 'New Announcement Published',
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': f'Date: {date}. Announcement: {message}',
                    'Charset': 'UTF-8'
                }
            }
        }

        # Send the email
        ses.send_email(
            Source='posd.announcements.aws@gmail.com',
            Destination={'ToAddresses': ['razvanalexandrunicu@gmail.com']},
            Message=message
        )
    return {"message": "Successfully handled event"}
"""
                ),
            handler='index.handler'
            )

        # Add DynamoDB stream as an event source to the Lambda function
        announcements_table.grant_read_data(sns_publisher_lambda)
        sns_publisher_lambda.add_event_source(dynamo_event.DynamoEventSource(announcements_table, starting_position=_lambda.StartingPosition.TRIM_HORIZON, batch_size=5, bisect_batch_on_error=True,retry_attempts=10))

        # Create IAM Groups used by the employees
        # (User)Admin, Engineer, Support Engineer, HumanResources
        engineering_group = iam.Group(self, "EngineeringDepartment", group_name="EngineeringDepartment")
        support_engineering_group = iam.Group(self, "SupportEngineerRole", group_name="SupportEngineeringDepartment")
        human_resources_group = iam.Group(self, "HumanResourcesRole", group_name="HumanResourcesDepartment")



        # Attach S3 permissions to groups for the approved_artifacts_bucket bucket
        
        # Policies for read-only
        bucket_read_policy = iam.PolicyStatement(
                actions=["s3:Get*", "s3:List*"],
                resources=[approved_artifacts_bucket.bucket_arn]
            )
        bucket_objects_read_policy = iam.PolicyStatement(
                actions=["s3:Get*"],
                resources=[approved_artifacts_bucket.arn_for_objects('*')]
            )

        # Policies for read-write
        bucket_read_write_policy = iam.PolicyStatement(
                actions=["s3:*"],
                resources=[approved_artifacts_bucket.bucket_arn]
            )
        bucket_objects_read_write_policy = iam.PolicyStatement(
                actions=["s3:*", ],
                resources=[approved_artifacts_bucket.arn_for_objects('*')]
            )

        # Permissions for Engineering department
        engineering_group.add_to_policy(bucket_read_policy)
        engineering_group.add_to_policy(bucket_objects_read_policy)

        # Permissions for Support Engineering department
        support_engineering_group.add_to_policy(bucket_read_write_policy)
        support_engineering_group.add_to_policy(bucket_objects_read_write_policy)

        # Attach DynamoDB permissions to groups
        announcements_table.grant_read_write_data(human_resources_group)
        announcements_table.grant_read_data(engineering_group)
        announcements_table.grant_read_data(support_engineering_group)

        # Allow lambda to send email with SES

        # Create the IAM policy for SES
        policy = iam.PolicyStatement(
            actions=["ses:SendEmail", "ses:SendRawEmail"],
            resources=["*"],
        )
        sns_publisher_lambda.add_to_role_policy(policy)



