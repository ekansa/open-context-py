from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest


class ComplexDescription():
    """
    methods for getting complex descriptions

    """
    ITEM_TYPE = 'complex-desciption'
    PREDICATE_COMPLEX_DES = 'oc-gen:has-complex-description'
    PREDICATE_COMPLEX_DES_LABEL = 'rdfs:label'
    
    def __init__(self):
        pass
    
    
