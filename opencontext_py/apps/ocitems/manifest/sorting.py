from math import pow
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.sorting import LinkEntitySorter


# This class prepares item sorting for Solr indexing and item display in Open Context
class ManifestSorter():
    """ Sort orders are recorded in numeric strings as so:

    '00-0000-000000-000000-000000-000000-000000-000000-000000'

    This first two digits record are highest level organizers for
    sorting in the oc_assertions table (so containment comes before
    variable predicates, which come before linking predicates, etc.)

    The next 4 digits store sort order based on project sort index.
    The rest of the digits store sort order in a nestet hiearchy.
    """

    def __init__(self):
        self.sorted_uris = []
        self.sorted_slugs = []

    def sort_subjects(self, project_uuid):
        pass

    def get_project_index(self, project_uuid):
        """ Gets the sort - index number for a project """
        act_proj_short_id = 0
        if(project_uuid != '0'):
            try:
                act_proj = Project.objects.get(uuid=project_uuid)
                act_proj_short_id = act_proj.short_id
            except Project.DoesNotExist:
                act_proj_short_id = 0
        return act_proj_short_id

    def sort_digits(self, index, digit_length=6):
        """ Makes a 3 digit sort friendly string from an index """
        if index >= pow(10, digit_length):
            index = pow(10, digit_length) - 1
        sort = str(index)
        if len(sort) < digit_length:
            while len(sort) < digit_length:
                sort = '0' + sort
        return sort



class UUIDListProjectItemType:
    '''
    The list of UUIDs for sorting
    '''
    def __init__(self, project_uuid, item_type):
        self.uuids = Manifest.objects.values_list(
            'uuid', flat=True)\
            .filter(project_uuid=project_uuid,
                    item_type=item_type
                    ).iterator()
