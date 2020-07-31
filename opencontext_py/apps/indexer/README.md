# README About Indexing

The file `solrdocumentnew.py` creates solr documents for indexing in according to the new Solr-8 schema. It is
not backwards compatible with the currently in production Solr-7 schema. Open Context `settings.py` now allows 
connections to two different solr instances, so one can connect to a legacy Solr-7 solr server and a new
Solr-8 solr server. To generate solr documents for indexing in a Solr-8 index, use `solrdocumentnew.py` as follow:

```
from django.conf import settings

from opencontext_py.apps.ocitems.manifest.models import Manifest

from opencontext_py.libs.solrconnection import SolrConnection

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew


# Make a list of UUIDs to index, this simply gets them all from
# the Manifest model
uuids = [m.uuid for m in Manifest.objects.all()]

# Connect to the new Solr-8 server (SOLR_HOST_TEST)
solr = SolrConnection(
    exit_on_error=False,
    solr_host=settings.SOLR_HOST_TEST,
    solr_port=settings.SOLR_PORT_TEST,
    solr_collection=settings.SOLR_COLLECTION_TEST
).connection

batch_size=20

batch = []
num_uuids = len(uuids)
print('Index {} items in batches of {}'.format(num_uuids, batch_size))
for i, uuid in enumerate(uuids, 1):
    print('[{} of {}] solr doc: {}'.format(i, num_uuids, uuid))
    sd_obj = SolrDocumentNew(uuid)
    sd_obj.make_solr_doc()
    batch.append(sd_obj.fields)
    if len(batch) < batch_size:
        continue
    print('-----------------------------------------------------')
    print('Indexing...')
    solr_status = solr.update(batch, 'json', commit=False).status
    solr.commit()
    batch = []
    print('-----------------------------------------------------')

# Index the last remaining batch
solr_status = solr.update(batch, 'json', commit=False).status
solr.commit()
print('Optimize...')
solr.optimize()
print('Done')
```

You should be able to search / query the Solr-8 instance via the new search module located in
`opencontext_py.apps.searcher.new_solrsearcher`. The URL path for the searching the Solr-8 instance
is located at `http://{your-host}/query/`. At this time, the HTML search interface is very bare-bones
and badly styled. It is strictly in an experimental stage to test basic functionality.

