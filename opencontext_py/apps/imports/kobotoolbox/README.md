# Open Context KoboToolBox Imports

This director holds a variety of functions to process data, exported from Kobotoolbox in the Excel (.xlsx) format.
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

