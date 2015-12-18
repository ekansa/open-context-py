import json
import reversion
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.edit.versioning.models import VersionMetadata


class DeletionRevision():
    """ This class contains methods
        for version control of deletions.
    """

    def __init__(self):
        self.project_uuid = False
        self.uuid = None
        self.item_type = None
        self.user_id = False
        self.manifest_keys = []  # primary key for deleted manifest items
        self.link_entity_keys = []  # primary key for deleted linked entities
        self.assertion_keys = []  # primary keys for deleted assertions
        self.link_annotation_keys = []  # primary keys for deleted link annotations
        self.identifier_keys = []  # primary keys for deleted stable identifiers
        self.mediafile_keys = []  # primary key for deleted mediafile items
        self.geospace_keys = []  # primary keys for deleting geospace data
        self.event_keys = []  # primary keys for deleting event data

    def save_delete_revision(self, label, json_note):
        """ Saves a revision metadata record
            for the deletion action. It includes
            information on the record keys that were
            deleted so as to make it easier
            to revert a deletion
        """
        keys_dict = LastUpdatedOrderedDict()
        keys_dict['oc_manifest'] = self.manifest_keys
        keys_dict['link_entities'] = self.link_entity_keys
        keys_dict['oc_assertions'] = self.assertion_keys
        keys_dict['link_annotations'] = self.link_annotation_keys
        keys_dict['oc_identifiers'] = self.identifier_keys
        keys_dict['oc_mediafiles'] = self.mediafile_keys
        keys_dict['oc_geospace'] = self.geospace_keys
        keys_dict['oc_events'] = self.event_keys
        keys_json = json.dumps(keys_dict,
                               indent=4,
                               ensure_ascii=False)
        if self.project_uuid is not False:
            # only version control if project_uuid is not False
            vm = VersionMetadata()
            vm.project_uuid = self.project_uuid
            vm.uuid = self.uuid
            vm.item_type = self.item_type
            vm.label = label
            vm.user_id = self.user_id
            vm.deleted_ids = keys_json
            vm.json_note = json_note
            vm.save()
