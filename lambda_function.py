import boto3
import datetime
import os
import json
from email.message import EmailMessage

# Needs:
#     AWSCertificateManagerReadOnly
#     AmazonSESFullAccess
#     IAMReadOnlyAccess
#     AWSLambdaBasicExecutionRole

CHARSET = "UTF-8"
REGIONS = ['eu-west-1', 'us-east-1']

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "ian@example.com")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "ian@example.com")
WEEKS_EXPIRY = int(os.environ.get("WEEKS_EXPIRY", "8"))

account_id = boto3.client('sts').get_caller_identity().get('Account')
SUBJECT = f"Certificate Expiry Report for {account_id}"


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


def arnToRegion(arn):
    return arn.split(":")[3]


def formatLoadBalancer(arn):
    splitter = arn.split(":")
    return f"{splitter[2]}:{splitter[5]}:"


def formatData(expiringSoon):
    body_text = "Certificate Name,Date of Expiry,Region,Where it is been used"
    for cert in sorted(expiringSoon, key=lambda i: i['Certificate']['NotAfter']):
        reg = arnToRegion(cert['Certificate']['CertificateArn'])
        dom = cert['Certificate']['DomainName']
        exp = cert['Certificate']['NotAfter'].strftime("%Y-%m-%d")
        # alt = json.dumps(cert['Certificate']['SubjectAlternativeNames'])
        used = []
        if len(cert['Certificate']['InUseBy']) > 0:
            for usage in cert['Certificate']['InUseBy']:
                used.append(formatLoadBalancer(usage))
        used = " ".join(used)
        body_text += f"\n{dom},{exp},{reg},{used}"
    body_html = body_text.replace('\n', '<br>')
    body_html = f"<html><pre>{body_html}</pre></html>"
    return body_text, body_html


def checkCerts():
    soon = datetime.datetime.utcnow() + datetime.timedelta(weeks=WEEKS_EXPIRY)
    expiringSoon = []

    for region in REGIONS:
        print(f"Region: {region}")
        client = boto3.client('acm', region_name=region)

        certArns = client.list_certificates()
        while True:
            for certArn in certArns['CertificateSummaryList']:
                cert = client.describe_certificate(CertificateArn=certArn['CertificateArn'])
                expiry = cert['Certificate']['NotAfter'].replace(tzinfo=None)
                domain = cert['Certificate']['DomainName']
                if expiry < soon:
                    expiringSoon.append(cert)
                    print(f"Expiring Soon: {domain} at {expiry}")
                    if len(cert['Certificate']['InUseBy']) > 0:
                        print("\tInUseBy:")
                        for usage in cert['Certificate']['InUseBy']:
                            print(f"\t\t{formatLoadBalancer(usage)}")

            if 'NextToken' in certArns:
                certArns = client.list_certificates(NextToken=certArns['NextToken'])
            else:
                break

    print(f"Len ExpiringSoon: {len(expiringSoon)}")

    return expiringSoon


def sendEmail(body_text, body_html):
    client = boto3.client('ses')

    # #Provide the contents of the email.
    # response = client.send_email(
    #     Destination={ 'ToAddresses': [ RECIPIENT_EMAIL ] },
    #     Message={
    #         'Body': {
    #             'Html': { 'Charset': CHARSET, 'Data': body_html },
    #             'Text': { 'Charset': CHARSET, 'Data': body_text },
    #         },
    #         'Subject': { 'Charset': CHARSET, 'Data': SUBJECT }
    #     },
    #     Source=SENDER_EMAIL
    # )

    msg = EmailMessage()
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.add_attachment(body_text, filename='report.csv')
    msg.get_payload()[0].set_type("text/csv")

    response = client.send_raw_email(
            Source=SENDER_EMAIL,
            Destinations=[ RECIPIENT_EMAIL ],
            RawMessage={
                'Data':msg.as_string(),
            }
        )

    print("Email sent! Message ID:"),
    print(response['MessageId'])


def lambda_handler(event, context):
    expiringSoon = checkCerts()
    body_text, body_html = formatData(expiringSoon)
    sendEmail(body_text, body_html)


if __name__ == '__main__':
    lambda_handler(None, None)
