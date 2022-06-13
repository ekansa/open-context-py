# Open Context KoboToolBox Imports (Revised Schema Update)

This directory holds a variety of functions to process data, exported from Kobotoolbox in the Excel (.xlsx) format.
It uses Pandas to load the data into dictionaries of dataframes for processing.

The main motivation for developing these functions was to serve the needs of the Poggio Civitate excavations. The
Poggio Civitate (PC) team is using KoboToolBox as their primary means of field data collection, photo documentation,
and object cataloging. Most of the functions in this directory are highly tailored for the specific needs of migrating
PC data collected by Kobotoolbox into Open Context. I did however try to consider broader applicability of some of these
functions so they can be used for Kobotoolbox created data from other archaeological projects, but please note that these
functions will need a great deal of revision and refactoring to make more generalized.


## Background
As of June 2022, KoboToolBox now has better support for forms that use external CSV files to configure pick lists, 
so the forms used by the PC team can now be updated using live data managed by Open Context. We can regenerate the
CSV files that configure pick lists periodically to make referential integrity easier to achieve between Kobo form
generated data and data managed in Open Context. 
