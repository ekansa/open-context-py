

from opencontext_py.apps.ldata.linkentities.models import (
    LinkEntity
)
from opencontext_py.apps.ldata.pleiades.api import pleiadesAPI


PLEIADES_VOCAB_URI = 'http://pleiades.stoa.org/'



def add_get_pleiades_place_entity(pleiades_uri):
    """Gets or adds a link_entity for a Pleiades URI"""
    le = LinkEntity.objects.filter(uri=pleiades_uri).first()
    if le:
        # Already in the database
        return le
    api = pleiadesAPI()
    label = api.get_place_title(pleiades_uri=pleiades_uri)
    print(
        f'Saving {pleiades_uri} as {label}'
    )
    le = LinkEntity()
    le.uri = pleiades_uri
    le.label = label
    le.alt_label = label
    le.vocab_uri = PLEIADES_VOCAB_URI
    le.ent_type = 'instance'
    le.sort = ''
    le.save()
    return le

