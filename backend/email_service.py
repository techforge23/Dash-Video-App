import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def send_email(sender, recipient, subject, content):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = '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'
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    email = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=[{"email": recipient}],
        subject=subject,
        html_content=content
    )

    try:
        api_response = api_instance.send_transac_email(email)
        print(api_response)
    except ApiException as e:
        print("Exception when calling TransactionalEmailsApi->send_transac_email: %s\n" % e)

