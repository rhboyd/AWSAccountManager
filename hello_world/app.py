import json
import email
import os
from email import policy
from email.parser import BytesParser, Parser
import boto3
import re

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
        print('To:', msg['to'])
        print('From:', msg['from'])
        print('Subject:', msg['subject'])
        simplest = msg.get_body(preferencelist=('plain', 'html'))
        body_text = ''.join(simplest.get_content().splitlines(keepends=True))
        account = get_account_info(msg['to'])

        response = ses_client.send_email(
            Source=msg['to'],
            Destination={
                'ToAddresses': [
                    account.internal_email_address
                ]
            },
            Message={
                'Subject': {
                    'Data': "{}: {}".format(account.account_id, msg['subject']),
                    'Charset': 'utf-8'
                },
                'Body': {
                    'Text': {
                        'Data': body_text,
                        'Charset': 'utf-8'
                    }
                }})

    return {
        "statusCode": 200,
        "body": json.dumps(response),
    }
