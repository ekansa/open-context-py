# About all_items.editorial.synchronize

These modules provide data export and import functionality to move records from an Open Context project from one instance to another.

The usual workflow has been to dump records serialized as JSON from one Open Context instance into a directory (created for a given project). The directory and contents get moved to another Open Context instance for loading.

This module requires connections between different databases. The production (`prod`) 
database is regarded as "the source of truth". All writes to the `prod` database from
a remote instance of Open Context can only be an **INSERT**. Update queries from 
remote instances to 'prod' are not allowed.

If connecting to a Google Cloud hosted database server, be sure to configure
`secrets.json` to use the Google Cloud sql proxy. To start the Google Cloud
sql proxy, use this invocation:


    ./cloud_sql_proxy -instances=<INSTANCE NAME>=tcp:5436


The Django will connect to the Cloud sql proxy at the local host, so make sure you
have a different port specified than your local Postgresql instance so the 
proxy connection to the Google Cloud database does not conflict with your 
local Postgres database connection.