# AWS

_If we keep ignoring usability bugs, the customers will fix them themselves. Ideally with Lambda._ --AWS, presumably 

This is an AWS Accounts Email Organizer. It will help users of AWS Organizations to keep track of which email addresses are tied to which accounts.

Here's how it works.

* You reserve a new domain name. It can be whatever you want. It doesn't "NEED" to stay private, but it's better if fewer people outside your Team know about it. For this example we will assume you reserved TwitterForPets.com

* Deploy the stack with the Domain:TwitterForPets.com, MyHostedZone:\[Public Hosted Zone ID that Route53 created for TwitterForPets.com\], DefaultEmail:Mike@TwitterForPets.com 

* When you create a new AWS Account in AWS Organizations, give the account a meaningful account name then pick whatever unused email address you want from your new domain, for example Corey@TwitterForPets.com. You don't have to do any other work to prepare the email address, you just need to make sure that it isn't in use by another one of your AWS Accounts.

* When the new AWS Account receives an email, a Lambda Function will look up the account email and account id and add them to a dynamoDB Table, then forward the email to the provided default email address with the subject line prepended with the account ID.

* You can update the table entry to point to any other email address you want. You can also update the table before the first email, but letting the first automatic one create the Item keeps me from making a typo.


You will need to cut a free support ticket to AWS Support to ask them to un-sandbox AWS SES inside your account. 

The current version of this app require that it be deployed in the root so that it can access AWS Organizations to dereference emails to account IDs. If you wanted to maintain the table yourself, you could put this stack in any account you wish.

# Installation

Installation is as a standard AWS SAM project, with 4 environment specific parameters:  

0) Clone the repo, if you haven't already

1) Have a bucket handy
    Your AWS account should have an S3 bucket, and a Route53 Hosted Zone 

2) Setup your 4 paramaters in environment variables
    ``` 
    export BUCKETNAME=<hole_in_the_bucket>
    export HOSTEDZONEID=<Z123456789A>
    export DOMAINNAME=<mybiglongdomainname.wtf>
    export DEFAULTEMAIL=<bigboss@smallco.com>
    ```

3) From a CLI with correct AWS access:
    ```
    sam build
    sam package --s3-bucket ${BUCKETNAME} --output-template-file output.yaml                     
    sam deploy --template-file ./output.yaml --stack-name AWS-Account-Manager-Email-Manager --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --parameter-overrides "MyHostedZone=${HOSTEDZONEID}" "DefaultEmail=${DEFAULTEMAIL}" "Domain=${DOMAINNAME}"
    ```

4) Create some accounts using AWS Organizations, and watch the emails flow.

    For a further challenge, try getting AWS Control Tower to create your accounts through Service Catalog & AWS Organizations
 
    _Its been releases GA, so should be fine_ -- said someone
 
    (Hint - change your Accounts email to use your new domainname before you try using Control Tower)
