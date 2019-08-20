import json
import os
import email
from email import policy
from email.parser import Parser
import boto3
from botocore.exceptions import ClientError

DEFAULT_EMAIL = os.environ['DEFAULT_EMAIL']

ses_client = boto3.client('ses')
s3 = boto3.resource('s3')
s3Client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

class AccountDeets(object):
    def __init__(self, email_address: str, account_id: str, internal_email_address: str):
        self._email_address = email_address
        self._account_id = account_id
        self._internal_email_address = internal_email_address

    @property
    def email_address(self) -> str:
        return self._email_address

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def internal_email_address(self) -> str:
        return self._internal_email_address


def get_account_info(email_address: str) -> AccountDeets:
    # Ensure we have only the email - not the realname part.
    _, email_address = email.utils.parseaddr(email_address)

    try:
        response = table.get_item(
            Key={
                'EmailAddress': email_address
            }
        )
        return AccountDeets(
            email_address=email_address,
            account_id=response['Item']['AccountId'],
            internal_email_address=response['Item']['InternalEmail']
        )
    except KeyError as e:
        orgs_client = boto3.client('organizations')
        paginator = orgs_client.get_paginator('list_accounts')
        response_iterator = paginator.paginate()
        for page in response_iterator:
            for account in page['Accounts']:
                if account['Email'] == email_address:
                    table.put_item(
                        Item={
                            'EmailAddress': account['Email'],
                            'AccountId': account['Id'],
                            'InternalEmail': DEFAULT_EMAIL
                        },
                    )
                    return AccountDeets(
                        email_address=account['Email'],
                        account_id=account['Id'],
                        internal_email_address=DEFAULT_EMAIL
                    )
        raise Exception("Account not found for Email Address")
    except Exception as e:
        print(e)
        raise Exception("Ya done goofed! Make sure you set the Table Name correctly and your permissions are good")


def lambda_handler(event, context):
    for record in event['Records']:

        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        obj = s3.Object(bucket, key)
        raw_contents = obj.get()['Body'].read()
        msg = Parser(policy=policy.default).parsestr(raw_contents.decode('utf-8'))

        orig_to = msg['to']
        orig_subject = msg['subject']

        print('To: ', msg['to'])
        print('From: ', msg['from'])
        print('Subject: ', msg['subject'])

        account = get_account_info(msg['to'])

        del msg['DKIM-Signature']
        del msg['Sender']
        del msg['subject']
        del msg['Source']
        del msg['From']
        del msg['Return-Path']

        msg['subject'] = "[{}]: {}".format(account.account_id, orig_subject)

        try:
            response = ses_client.send_raw_email(
                RawMessage=dict(Data=msg.as_string()),
                Destinations=[
                    account.internal_email_address
                ],
                Source=orig_to
            )
        except ClientError as e:
            print(e.response['Error']['Message'])
            raise e
        else:
            print("Email sent. Message ID: ", response['MessageId'])

    return {
        "statusCode": 200,
        "body": json.dumps(response),
    }
