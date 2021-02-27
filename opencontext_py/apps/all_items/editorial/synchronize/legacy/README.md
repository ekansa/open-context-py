# About all_items.editorial.synchronize.legacy

These modules provide data export and import functionality to move legacy schema
records from an Open Context project from one instance to another.

If connecting to a Google Cloud hosted database server, be sure to configure
`secrets.json` to use the Google Cloud sql proxy. To start the Google Cloud
sql proxy, use this invocation:


    ./cloud_sql_proxy -instances=<INSTANCE NAME>=tcp:5434


The Django will connect to the Cloud sql proxy at the local host, so make sure you
have a different port specified than your local Postgresql instance so the 
proxy connection to the Google Cloud database does not conflict with your 
local Postgres database connection.