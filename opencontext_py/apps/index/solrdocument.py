import datetime
from opencontext_py.apps.ocitems.ocitem.models import OCitem


class SolrDocument:

    def __init__(self, uuid):
        self.uuid = uuid
        self.text = 'blah ' + uuid
        self.updated = datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%SZ')
        self.image_media_count = 0
        self.other_binary_media_count = 0
        self.sort_score = 0
        self.interest_score = 0
        self.project_uuid = uuid
        self.published = datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%SZ')
        self.document_count = 0
        self.uuid_label = 'blah' + uuid
