from django.conf import settings
from opencontext_py.apps.imports.fields.models import ImportField 

class KoboFields():
    """ 
    used to classify an imported field from Refine
    if it matches an automatically generated field name from
    kobotoolbox
    """

    def __init__(self):
        self.fields = [
            '__version__',
            '_uuid',
            '_submission_time',
            '_tags',
            '_notes'  
        ]
        self.field_type = 'metadata'
    
    def classify_if_kobofield(self, imp_f):
        """ classifies an import field object if
            it has a name that matches the
            Kobotoolbox field names
        """
        if isinstance(imp_f, ImportField):
            match = False
            for field in self.fields:
                if imp_f.label == field:
                    match = True
                elif imp_f.ref_name == field:
                    match = True
                elif imp_f.ref_orig_name == field:
                    match = True
                if match:
                    break
            if match:
                imp_f.field_type = self.field_type
        return imp_f