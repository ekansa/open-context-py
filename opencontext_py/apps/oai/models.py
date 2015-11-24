import lxml
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict


class OAIpmh():
    """
    Open Archives Initiative, Protocol for Metadata
    Harvesting Methods
    """
    
    def __init__(self, id_href=True):
        self.http_resp_code = 200
        self.errors = []

    def process_verb(self, request):
        """ processes a request verb,
            determines the correct
            responses and http response codes
        """
        output = False
        if 'verb' in request.GET:
            verb = request.GET['verb']
            if verb == 'Identify':
                output = self.make_identifiy()
        return output
    
    def make_identify(self):
        """ Makes the XML for the
            Identify verb
        """
        output = False
        return output