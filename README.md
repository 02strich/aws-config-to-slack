# AWS Config to Slack

Sends daily breakdowns of AWS config resources to a Slack channel.

# Install

1. Install [`serverless`](https://serverless.com/), which I use to configure the AWS Lambda function that runs daily.

    ```
    npm install -g serverless
    ```

1. Create an [incoming webhook](https://www.slack.com/apps/new/A0F7XDUAZ) that will post to the channel of your choice on your Slack workspace. Grab the URL for use in the next step.

1. Install pipenv

    ```
    pip install pipenv
    ```

1. Install serverless python requirements

    ```
    serverless plugin install -n serverless-python-requirements
    ```

1. Deploy the system into your AWS account, replacing the webhook URL, audit role arn and Config Aggregator Name below with the matching ones for your setup.

    ```
    serverless deploy --stage="prod" --param="audit_role_arn=arn:aws:iam::<AUDIT ACCOUNT ID>:role/aws-config-to-slack" --param="aggregator_name=aws-controltower-GuardrailsComplianceAggregator" --param="slack_url=https://hooks.slack.com/services/xxx/yyy/zzzz"
    ```

## Other Useful CLI Arguments Related to your AWS account

By default, `AWS_PROFILE` and `AWS_REGION` are defaulting to `default` and `us-east-1`. These value can be changed by modifying the environment. For aws account, sensible default is attempted to be retrieved. For example, boto3 is used to try and determine your AWS account alias if it exists, and if not your AWS account ID.
Additionally, for your AWS region the environment variables `AWS_REGION`, then `AWS_DEFAULT_REGION` are read and used if present, otherwise fallback to 'us-east-1' (N. Virginia).

    ```
    AWS_PROFILE="default" AWS_REGION="eu-west-1" serverless deploy \
        --param "slack_url=https://hooks.slack.com/services/xxx/yyy/zzzz" \
        --param "aws_account=my custom account name"
    ```
