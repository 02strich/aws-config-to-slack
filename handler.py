import datetime
import logging
import os
from dateutil.tz import tzlocal
from typing import Mapping, List, Optional

import botocore
import botocore.credentials
import botocore.session
import boto3
import boto3.session
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    account_mapping_table = get_account_map()

    # assume role
    audit_session = assumed_role_session(os.environ.get('AUDIT_ROLE_ARN') or "")

    # list resources
    ec2_instances = list_resources(audit_session, os.environ.get('AGGREGATOR_NAME') or "", account_mapping_table, "AWS::EC2::Instance")
    eks_clusters = list_resources(audit_session, os.environ.get('AGGREGATOR_NAME') or "", account_mapping_table, "AWS::EKS::Cluster")
    elbs = list_resources(audit_session, os.environ.get('AGGREGATOR_NAME') or "", account_mapping_table, "AWS::ElasticLoadBalancing::LoadBalancer")
    elbs += list_resources(audit_session, os.environ.get('AGGREGATOR_NAME') or "", account_mapping_table, "AWS::ElasticLoadBalancingV2::LoadBalancer")

    slack_hook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if slack_hook_url:
        publish_slack(slack_hook_url, eks_clusters, elbs, ec2_instances)

def assumed_role_session(role_arn: str, base_session: Optional[botocore.session.Session] = None) -> boto3.Session:
    base_session = base_session or boto3.session.Session()._session
    fetcher = botocore.credentials.AssumeRoleCredentialFetcher(
        client_creator = base_session.create_client,
        source_credentials = base_session.get_credentials(),
        role_arn = role_arn,
        extra_args = {
        #    'RoleSessionName': None # set this if you want something non-default
        }
    )

    creds = botocore.credentials.DeferredRefreshableCredentials(
        method = 'assume-role',
        refresh_using = fetcher.fetch_credentials,
        time_fetcher = lambda: datetime.datetime.now(tzlocal())
    )

    botocore_session = botocore.session.Session()
    botocore_session._credentials = creds
    return boto3.Session(botocore_session = botocore_session)

def get_account_map() -> Mapping[str, str]:
    result: Mapping[str, str] = {}

    client = boto3.client('organizations')
    paginator = client.get_paginator("list_accounts")
    for page in paginator.paginate():
        for account in page.get("Accounts", []):
            result[account["Id"]] = account["Name"]

    return result

def list_resources(session: boto3.Session, configuration_aggregator_name: str, account_map: Mapping[str, str], resource_type: str) -> List[str]:
    result: List[str] = []

    client = session.client('config')
    paginator = client.get_paginator("list_aggregate_discovered_resources")
    for page in paginator.paginate(ConfigurationAggregatorName=configuration_aggregator_name, ResourceType=resource_type):
        for resource in page.get("ResourceIdentifiers", []):
            result.append(f"*{account_map[resource['SourceAccountId']]}*: {resource['ResourceId']} @ {resource['SourceRegion']}")

    return result

def publish_slack(hook_url: str, eks_clusters: List[str], elbs: List[str], ec2_instances: List[str]) -> None:
    payload = {
        "blocks": []
        }

    if eks_clusters:
        payload["blocks"].append( {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":eks: EKS Clusters",
                "emoji": True
            }
        })
        payload["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join("- " + entry for entry in eks_clusters),
            }
        })
    
    if elbs:
        payload["blocks"].append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":elb: Load Balancers",
                "emoji": True
            }
        })
        payload["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join("- " + entry for entry in elbs),
            }
        })
    
    if ec2_instances:
        payload["blocks"].append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":ec2: EC2 Instances",
                "emoji": True
            }
        })
        payload["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join("- " + entry for entry in ec2_instances),
            }
        })

    resp = requests.post(
        hook_url,
        json=payload,
    )

    if resp.status_code != 200:
        logger.warning("HTTP %s: %s" % (resp.status_code, resp.text))
