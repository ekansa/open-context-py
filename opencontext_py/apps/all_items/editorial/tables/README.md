# About all_items.editorial.tables

This module has several functions used to make exports of tabular data
from Open Context.

Because Open Context publishes data from many different sources,
and each source may have its own unique set of descriptive attributes
and relations, Open Context mainly organizes data in "graph" structures.
While a graph structure suites heterogenous data, it is unfamiliar and
hard for analysis or visualization by typical users. This feature exports
data into more convenient and user-friendly tables.

These functions include the following:

1. `create_df.py`: This has the main logic for creating an export of
   data from Open Context. You can pass AllAssertions filters and exclusions
   and a other optional arguments to select data for export. These
   functions are centered on the creation and manipulation of Pandas
   Dataframes.

2. `queue_utilities.py`: These functions add some Redis-cache stored state
   information and Redis Queue (django-rq) wrapping of `create_df` functions.
   Because export table generation can take some minutes, a queue worker
   will need to be running to queue export jobs while responding in a timely
   manner to the Web front-end interface. Completed export dataframes get
   cached by Redis for about 6 hours, so they can be reviewed or discarded
   without publishing. Start the worker with:
   `python manage.py rqworker high`

3. `ui_utilities.py`: These functions return dicts that configure the Vue.js and
    Bootstrap user interface for making export tables.

4. `cloud_utilties.py`: These functions actually put export tables into 
   a cloud-storage container (bucket). In this way, export tables can be
   saved and published.

5. `metadata.py`: These are functions to add metadata (AllAssertion)
   objects and AllResource objects for published export tables that are 
   added to the AllManifest table.
