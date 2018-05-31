from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from django.contrib.humanize.templatetags.humanize import intcomma


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
        # self.user_phone = ''
        self.project_name = ''
        self.is_grad_student = False
        self.duration = 0
        self.count_spec_datasets = 0
        self.count_tables = 0
        self.count_images = 0
        self.count_docs = 0
        self.count_gis = 0
        self.count_other = 0
        self.comments = ''
        self.license_uri = False
        self.license_label = ''
        self.license_note = ''
        self.base_cost = 250  # minimum cost for publishing
        self.max_cost = 7750  # maximum cost for an estimate
        self.image_cost = 5
        self.other_cost = 20
        self.doc_cost = 15
        self.gis_cost = 25
        self.raw_cost = 0
        self.errors = []

    def process_estimate(self, post_data):
        """ processes an estimate """
        if False:
            # disable personal information
            if 'user_name' in post_data:
                self.user_name = post_data['user_name'].strip()
                if len(self.user_name) < 1:
                    self.user_name = '[Unnamed researcher]'
            if 'user_email' in post_data:
                try:
                    validate_email(post_data['user_email'])
                except ValidationError as e:
                    self.user_email = '[No valid email provided]'
                    self.errors.append('Need a valid email to send estimate results')
                else:
                    self.user_email = post_data['user_email'].strip()
            if 'project_name' in post_data:
                self.project_name = post_data['project_name'].strip()
                if len(self.project_name) < 1:
                    self.project_name = '[Unnamed project]'
        if 'is_grad_student' in post_data:
            if post_data['is_grad_student'] == '1':
                self.is_grad_student = True
            else:
                self.is_grad_student = False
        if 'duration' in post_data:
            try:
                duration = float(post_data['duration'])
            except:
                duration = 0
            self.duration = duration
        if 'count_spec_datasets' in post_data:
            try:
                count_spec_datasets = float(post_data['count_spec_datasets'])
            except:
                count_spec_datasets = 0
            self.count_spec_datasets = count_spec_datasets
        if 'count_tables' in post_data:
            try:
                count_tables = float(post_data['count_tables'])
            except:
                count_tables = 0
            self.count_tables = count_tables
        if 'count_images' in post_data:
            try:
                count_images = float(post_data['count_images'])
            except:
                count_images = 0
            self.count_images = count_images
        if 'count_docs' in post_data:
            try:
                count_docs = float(post_data['count_docs'])
            except:
                count_docs = 0
            self.count_docs = count_docs
        if 'count_gis' in post_data:
            try:
                count_gis = float(post_data['count_gis'])
            except:
                count_gis = 0
            self.count_gis = count_gis
        if 'count_other' in post_data:
            try:
                count_other = float(post_data['count_other'])
            except:
                count_other = 0
            self.count_other = count_other
        if False:
            if 'comments' in post_data:
                self.comments = post_data['comments'].strip()
                if len(self.comments) < 1:
                    self.comments = '[No additional user comments]'
            if 'license_uri' in post_data:
                self.license_uri = post_data['license_uri'].strip()
                self.license_label = self.get_license_label(self.license_uri)
            if 'license_note' in post_data:
                self.license_note = post_data['license_note'].strip()
                if len(self.license_note) < 1:
                    self.license_note = '[No additional licensing comments]'
        output = LastUpdatedOrderedDict()
        output['cost'] = self.estimate_cost()
        output['dollars'] = self.format_currency(output['cost'])
        output['raw_estimate'] = self.raw_cost
        output['label'] = self.project_name
        # output['email'] = self.user_email
        # output['name'] = self.user_name
        output['errors'] = self.errors
        return output

    def estimate_cost(self):
        """ Estimates the cost, in us dollars """
        cost = (self.base_cost * (self.duration * .5)) \
            + (self.base_cost * (self.count_spec_datasets * .75)) \
            + (self.base_cost * (self.count_tables * .5)) \
            + (self.image_cost * ((self.count_images + 10) / 15)) \
            + (self.doc_cost * ((self.count_docs + 10) / 15)) \
            + (self.gis_cost * ((self.count_gis + 5) / 5)) \
            + (self.other_cost * ((self.count_other + 10) / 5))
        if cost < self.base_cost:
            cost = self.base_cost
        if self.is_grad_student:
            cost = cost * .75
        self.raw_cost = round(float(cost), 2)
        if cost > self.max_cost:
            cost = self.max_cost
            self.max_cost_more = True
        return cost

    def format_currency(self, dollars):
        """ Provides a cost estimate in formatted dollars """
        dollars = round(float(dollars), 2)
        return "$%s%s" % (intcomma(int(dollars)), ("%0.2f" % dollars)[-3:])

    def get_license_label(self, license_uri):
        """ gets the label for the license,
            not many allowed choices, so no need for database lookup
        """
        if 'creativecommons.org' in license_uri:
            if 'publicdomain' in license_uri:
                label = 'Creative Commons Zero (CC-0); Public Domain'
            elif 'licenses/by' in license_uri:
                label = 'Creative Commons Attribution (CC-BY)'
        else:
            label = 'Other licensing provisions required'
        return label

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
