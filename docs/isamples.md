# iSamples and Open Context

Open Context publishes a wide variety of archaeological data documenting regions, sites, archaeological features 
(non-portable features of envirnonment altered by human activity like walls, buildings, canals, pits, etc.), as well records
documenting artifacts and ecofacts that are more relevant to the iSamples project. Open Context has "Extract, Transform
Load" (ETL) workflows to ingest data from many sources that all have different relationships, different descriptive 
attributes, and different controlled vocabularies. Because there are very few widely adopted data standards or common 
conventions in archaeology Open Context has a very generalized and abstract database schema to accomodate this 
diversity. Where we can, we link certain project (dataset) specific properties and controlled vocabulary terms to
other public data (ontologies, gazetteers, controlled vocabularies, etc.).


Open Context has a variety of [API services, see documentation](https://opencontext.org/about/services). Some APIs will
not be as useful for large-scale harvesting of records into iSamples. We're currently
busy with a major refactoring effort to improve the speed and scalability of these APIs, but until these updates are
ready, the approach described here will be fastest and easiest for initial harvesting by iSamples.


iSamples Requests for Simple Paged JSON:
[https://opencontext.org/subjects-search/.json?response=metadata%2Curi-meta&sort=updated--desc&rows=200&prop=oc-gen-cat-sample-col||oc-gen-cat-bio-subj-ecofact||oc-gen-cat-object&add-attribute-uris=1&attributes=obo-foodon-00001303,oc-zoo-has-anat-id,cidoc-crm-p2-has-type,cidoc-crm-p45-consists-of,cidoc-crm-p49i-is-former-or-current-keeper-of,cidoc-crm-p55-has-current-location,dc-terms-temporal,dc-terms-creator,dc-terms-contributor](https://opencontext.org/subjects-search/.json?response=metadata%2Curi-meta&sort=updated--desc&rows=200&prop=oc-gen-cat-sample-col||oc-gen-cat-bio-subj-ecofact||oc-gen-cat-object&add-attribute-uris=1&attributes=obo-foodon-00001303,oc-zoo-has-anat-id,cidoc-crm-p2-has-type,cidoc-crm-p45-consists-of,cidoc-crm-p49i-is-former-or-current-keeper-of,cidoc-crm-p55-has-current-location,dc-terms-temporal,dc-terms-creator,dc-terms-contributor)

The above requests currently fetches from Open Context 813,304 records about artifacts, ecofacts, and "samples" (sometimes descriptions of soil deposits, sometimes these are "bulk finds" like aggregated counts of different types of plant remains from a deposit). This request returns the maximum 200 rows (records) of data allowed. 

The following highlights a few useful aspects of the JSON response:

  * `"totalResults"` is the totaly number of results in this query
  * `"next-json"` is the link to the next page of results
  * `"last-json"` is the link to the lasg page of results
  * `"oc-api:has-results"` contains the list of individual records (where each record is returned as a relatively simple, "flat" dictionary of keys and values for different metadata attributes)
  
 
 


