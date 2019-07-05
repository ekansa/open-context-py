# Open Context KoboToolBox Imports

This directory holds a variety of functions to process data, exported from Kobotoolbox in the Excel (.xlsx) format.
It uses Pandas to load the data into dictionaries of dataframes for processing.

The main motivation for developing these functions was to serve the needs of the Poggio Civitate excavations. The
Poggio Civitate (PC) team is using KoboToolBox as their primary means of field data collection, photo documentation,
and object cataloging. Most of the functions in this directory are highly tailored for the specific needs of migrating
PC data collected by Kobotoolbox into Open Context. I did however try to consider broader applicability of some of these
functions so they can be used for Kobotoolbox created data from other archaeological projects, but please note that these
functions will need a great deal of revision and refactoring to make more generalized.

## Invoking This:
At the highest level, the main functions to process files and load into the Open Context database are located in `etl.py`.
The assumption is that you have exported datasets from Kobotoolbox in the Excel format, and have them located in a 
single directory in a local filesystem. Image files exported from Kobotoolbox will be extracted from their ZIP download
and in an "attachments" directory. The configuration globals scattered around these functions will need updating to
reflect the specifics for how to process different files exported from Kobotoolbox. 

To actually process the data invoke the following in Open Context's Python shell:
```
from opencontext_py.apps.imports.kobotoolbox.etl import (
    make_kobo_to_open_context_etl_files,
    update_open_context_db,
)
# STEP 1:
# Process raw data exported from Kobo to make datafiles that cross-reference
# uuids from different files and cross-reference with uuids already in 
# Open Context. This step generates several CSV files of processed and
# cross-referenced data that will actually get used to load into Open Context.
# This step does NOT alter the Open Context database.
make_kobo_to_open_context_etl_files()

# STEP 2:
# Load the processed and cross-referenced data files into the Open Context
# database. These steps will be somewhat easier to generalize for different
# datasets other than Poggio Civitate.
update_open_context_db()
```

## What Happens
Data captured in the field typically has many implicit relationships and needs some contextualiztion to be
intelligible, at least that's the main assumption in the workflows and transformations that go into
Open Context's ETL (extract, transform, load) processes. Data from Kobotoolbox forms used for Poggio Civitate
field recording similarly get several transformations and additions through this software process. These
include:

1. This ETL process preserves and reuses the UUIDs minted by Kobotoolbox. This will enable one to traceback
the specific origin of specific records of data.
2. All of the locations and objects (Open Context's `"item_type":"subjects"`) described and referenced in 
the Kobotoolbox form dataget extracted and consolidated into the `all-contexts-subjects.csv` file. This file
describes spatial containment hierarchies including containment relations with existing entities already in
Open Context's database. The "Unit ID" entities, which are not explicit in the Poggio Civitate kobotoolbox
data get generated in this process.
3. This ETL process gathers all media files (typically images) and their descriptions from all of the 
Kobotoolbox forms into a consolidated `all-media-files.csv` file. During this process, we check that each
given media file is actually present in the attachments directory, and we make full, preview, and thumbnail
versions of each file for upload to an image server. URLS to the images online are also generated.
4. This process also makes cleaned up attribute data files. Empty unused attribute columns get dropped, and
multivalue attribute columns get processed for easier review and import into Open Context's primary data
import pipeline. Hiearchic taxonomies also get processed to be consistent with already imported controlled
vocabularies.
5. The Poggio Civitate ETL process also checks on coordinates for the project's local grid, and reports on
outlier values that may be unreasonable data entry errors. It also reprojects the project's local grid
coordinates to the global WGS84 EPSG:4326 system.
6. The ETL process generates a general "trench book" entity and "Has Part", "Is Part of" relationships between
different trench book entries. It also generates "Next Entry" and "Previous Entry" relationships between
tench book entries to enable sequential navigation of trench book entries.
7. Linking relationships, including stratigraphic relations, between loci, small finds, bulk finds, 
trench book entries, media files, and cataloged objects get extracted, inferred, and validated. These get
output in files starting with `links--`. Each of these links files will have different columns with attributes
describing the entities getting linked. However, on import the only columns used are the `subject_uuid`, the
link link relation column (defaults to: `LINK_RELATION_TYPE_COL = 'Relation_type'`), and the `object_uuid` column.

## TODO:
1. Reorganize these functions. Move Poggio Civitate specific functions into a sub-directory "poggio_civitate".
2. Reorganize, consolidate, and simplify configuration globals. Most of these globals are specific to Poggio Civitate,
and will need to be generalized for other uses.



## Background
Unfortunately, as of July 2019, KoboToolBox does not very well support forms that use external
CSV files to configure pick lists, so the forms used by the PC team are pretty static. These forms do not support
look ups of live data published by Open Context, and because the Kobotoolbox does not (fully) support use of external
CSVs, we can't use Open Context to periodically update CSV encoded picklists for data capture forms. Therefore, assignment
and references of different identififiers for finds, objects, loci, trench books, etc. is still pretty manual and
error prone.

