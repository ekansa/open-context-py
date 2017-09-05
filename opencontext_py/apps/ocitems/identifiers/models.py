import hashlib
import reversion  # version control object
from django.db import models


# OCstring stores stable identifiers of various types
@reversion.register  # records in this model under version control
class StableIdentifer(models.Model):

    ID_TYPE_PREFIXES = {'ark': 'https://n2t.net/ark:/',
                        'doi': 'https://doi.org/',
                        'orcid': 'https://orcid.org/'}

    hash_id = models.CharField(max_length=50, primary_key=True)
    stable_id = models.CharField(max_length=200, db_index=True)
    stable_type = models.CharField(max_length=50)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.stable_id) + " " + str(self.stable_type) + " " + str(self.uuid)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def type_uri_check(self, stable_type, stable_id):
        """ returns the type of identifier in a stable_id
            if it has a uri prefix in it. If there's no
            recognized uri prefix, then just return the stable_type
            supplied in the method
        """
        output = stable_type
        for id_type, id_prefix in self.ID_TYPE_PREFIXES.items():
            if id_prefix in stable_id:
                # stable ID has a recognized type
                output = id_type
        return output

    def type_check_update(self):
        """ checks to see if the id has a URI prefix
            that matches a given type.
            if it does, then update the stable_type
            and remove the URI prefix
        """
        self.stable_id = self.stable_id.strip()
        for id_type, id_prefix in self.ID_TYPE_PREFIXES.items():
            if id_prefix in self.stable_id:
                # the user supplied a URI version of the stable ID
                self.stable_type = id_type
                self.stable_id = self.stable_id.replace(id_prefix, '')
            abrv_prefix = id_type + ':'
            if abrv_prefix in self.stable_id:
                self.stable_type = id_type
                self.stable_id = self.stable_id.replace(abrv_prefix, '')

    def save(self, *args, **kwargs):
        """
        saves a StableIdentifier item checking
        for type in the ID
        """
        self.type_check_update()
        self.hash_id = self.make_hash_id()
        super(StableIdentifer, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_identifiers'
