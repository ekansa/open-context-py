from django.db import models
from opencontext_py.apps.ldata.linkentities.models import LinkEntity


# This class stores linked data annotations made on the data contributed to open context
class LinkEntitySorter():

    def __init__(self):
        self.sorted_uris = []
        self.sorted_slugs = []

    def sort_ld_entity_list(self, linked_entity_list):
        """ Sorts the linked entities in a list """
        sort_list = []
        sort_qset = LinkEntity.objects\
                              .values_list('uri', flat=True)\
                              .filter(uri__in=linked_entity_list)\
                              .order_by('sort', 'uri')
        for uri in sort_qset:
            sort_list.append(uri)
        for uri in linked_entity_list:
            if uri not in sort_list:
                sort_list.append(uri)  # make sure we've got them all, even not found
        self.sorted_uris = sort_list
        return self.sorted_uris
