from opencontext_py.libs.general import LastUpdatedOrderedDict


class metaARK():
    """ Metadata object for ARK identifiers
    """

    META_PROFILE = 'erc'

    def __init__(self):
        self.who = None
        self.what = None
        self.when = None
        self.verbatim_id = None

    def make_who_list(self, who_list):
        """converts a list of 'who' (authors, contributors, creators)
           into a string for ezid
        """
        if isinstance(who_list, list):
            # make a properly formatted string
            self.who = '; '.join(who_list)
        elif isinstance(who_list, str):
            # already a a string
            self.who = who_list
        else:
            # a problem
            self.who = None

    def make_metadata_dict(self):
        """ make a dictionary object of the metadata """
        metadata = LastUpdatedOrderedDict()
        if isinstance(self.who, list):
            self.make_who_list(make_who_list)
        metadata[(self.META_PROFILE + '.who')] = str(self.who)
        metadata[(self.META_PROFILE + '.what')] = str(self.what)
        metadata[(self.META_PROFILE + '.when')] = str(self.when)
        if self.verbatim_id:
            metadata[(self.META_PROFILE + '.verbatim_id')] = str(self.verbatim_id)
        return metadata
