from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class metaDOI():
    """ Methods for making metadata objects for DOI identifiers
    """

    DEFAULT_META_PROFILE = 'datacite'
    
    def __init__(self):
        self.meta_profile = self.DEFAULT_META_PROFILE
        self.creator = None
        self.publisher = 'Open Context'
        self.publicationyear = None
        self.title = None
        self.resourcetype = 'Dataset'
    
    def make_creator_list(self, creator_list):
        """converts a list of 'creators' (authors, contributors, creators)
           into a string for ezid
        """
        if isinstance(creator_list, list):
            # make a properly formatted stcreator_listring
            self.creator = '; '.join(creator_list)
        elif isinstance(creator_list, str):
            # already a a string
            self.creator = creator_list
        else:
            # a problem
            self.creator = None
    
    def make_metadata_dict(self):
        """ make a dictionary object of the metadata """
        metadata = LastUpdatedOrderedDict()
        if isinstance(self.creator, list):
            self.make_creator_list(self.creator)
        if isinstance(self.publicationyear, str):
            if '-' in self.publicationyear:
                # we have a date, by default in OC as yyyy-mm-dd
                pub_ex = self.publicationyear.split('-')
                self.publicationyear = pub_ex[0]  # first value is the year value
        metadata[(self.meta_profile + '.creator')] = str(self.creator)
        metadata[(self.meta_profile + '.title')] = str(self.title)
        metadata[(self.meta_profile + '.publisher')] = str(self.publisher)
        metadata[(self.meta_profile + '.publicationyear')] = str(self.publicationyear)
        metadata[(self.meta_profile + '.resourcetype')] = str(self.resourcetype)
        return metadata
