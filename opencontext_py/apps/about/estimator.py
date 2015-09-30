from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
 
"""
from opencontext_py.apps.about.estimator import CostEstimator
est = CostEstimator()
est.send_test_email('kansaeric@gmail.com')
"""


class CostEstimator():

    """
    Estimates costs for a data publication
    """

    def __init__(self):
        rp = RootPath()
        base_url = rp.get_baseurl()
        self.href = base_url + '/about/estimate'  # URL for this
        self.estimate_id = False
        self.user_name = ''
        self.user_email = False
        self.user_phone = ''
        self.project_name = ''
        self.is_grad_student = False
        self.duration = 0
        self.count_spec_datasets = 0
        self.count_tables = 0
        self.count_images = 0
        self.count_video = 0
        self.count_docs = 0
        self.count_gis = 0
        self.count_other = 0
        self.comments = ''
        self.license_uri = False
        self.license_label = ''
        self.license_note = ''

    def send_test_email(self, to_email_addresses):
        """ Sends a test email
        """
        email_subject = 'Test Email from Open Context 3'
        email_message = 'Just checking if this works...'
        if not isinstance(to_email_addresses, list):
            to_email_addresses = [to_email_addresses]
        valid_emails = []
        for to_email_address in to_email_addresses:
            try:
                validate_email(to_email_address)
            except ValidationError as e:
                print("oops! wrong email: " + to_email_address)
            else:
                valid_emails.append(to_email_address)
        if len(valid_emails) > 0:
            send_mail(email_subject,
                      email_message,
                      settings.DEFAULT_FROM_EMAIL,
                      valid_emails,
                      fail_silently=False)
