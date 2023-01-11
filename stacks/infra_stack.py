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
                def handler(event, context):
                    print("Event:", event)
                    return {"message": "Successfully wrote event to the console"}
                """
                ),
            handler='index.handler'
            )

        # Add DynamoDB stream as an event source to the Lambda function
        announcements_table.grant_read_data(sns_publisher_lambda)
        sns_publisher_lambda.add_event_source(dynamo_event.DynamoEventSource(announcements_table, starting_position=_lambda.StartingPosition.TRIM_HORIZON, batch_size=5, bisect_batch_on_error=True,retry_attempts=10))

        # Create IAM Roles used by the employees
        # (User)Admin, Engineer, Support Engineer, HumanResources
        engineer_role = iam.Role(self, "EngineerRole", role_name="EngineerRole", assumed_by=iam.AccountPrincipal('593177338706'))
        support_engineer_role = iam.Role(self, "SupportEngineerRole", role_name="SupportEngineerRole", assumed_by=iam.ArnPrincipal('593177338706'))
        human_resources_role = iam.Role(self, "HumanResourcesRole", role_name="HumanResourcesRole", assumed_by=iam.ArnPrincipal('593177338706'))



        # Attach S3 permissions to roles for the approved_artifacts_bucket bucket
        support_engineer_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
                resources=[approved_artifacts_bucket.bucket_arn]
            )
        )
        engineer_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[approved_artifacts_bucket.bucket_arn]
            )
        )

        # Attach DynamoDB permissions to roles
        announcements_table.grant_read_write_data(human_resources_role)
        announcements_table.grant_read_data(engineer_role)
        announcements_table.grant_read_data(support_engineer_role)


