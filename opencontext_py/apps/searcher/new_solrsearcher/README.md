# README: Refactoring Search

This directory of code had incremental progress on refactoring Open Context's search functionality.

This does nothing to change the existing search features. It is a new project to attempt to make the 
existing convoluted, complicated, obscure and highly redundant code into something that is easier to 
understand and maintain.

## General architecture
Open Context defines a very abstract and not particularly user-friendly schema for indexing documents
(all the Manifest items) in Solr. We have lots of abstraction in the solr schema because we have to
ingest data from different projects, all of which have their own descriptive attributes and controlled
vocabularies. So Open Context uses a very abstract Solr schema, with many, many dynamic fields to
represent the schemas of different project datasets.

To make this abstraction easier to work with, Open Context does the following:

- Open Context has a query syntax that it exposes to the outside world for clients to use 
(see: https://opencontext.org/about/services#tab_query-syntax). Open Context translates requests from
outside clients into a query uses solr's query syntax and (super abstract) schema.
- Solr response with results in the form of a big JSON-encoded dictionary object. Open Context then
translates these Solr results into different output options, defaulting to a JSON-LD + GeoJSON 
output. 
- To make things easier for clients, Open Context's default JSON-LD + GeoJSON output has lots of links
the client can use to change state (sort, page, filter in different ways).



## A few things to understand first:

- Open Context uses solr dynamic fields to represent project specific attributes
(descriptive properties); projects; spatial contexts; and other metadata.
- Open Context uses "slugs" to identify entities in the database ("LinkedEntities", and
"Manifest" items) for both solr fields and the values in these solr fields.
- The dynamic Solr fields come in varieties for different data-types, differentiated by
their suffixes. The "id" data-type is used for entities stored in the database. The solr data types
that we use are: `id` for non-literal database entities; `int` for integer or boolean literals;
`double` for double precision floats; `date` for date-time values; `string` for text literal
values.


## Dynamic "id" fields and filter queries:
Dynamic fields for the "id" data-type are used to search / query / filter non-literal entities
stored in the database. These entities are identified by their "slugs". However, the values in
solr "id" dynamic fields are not simple slugs. Instead they are strings specially formatted to
make querying and faceting easier and less reliant on database lookups. 

The general pattern for values stored in dynamic "id" fields is as follows:
```{slug with dashes replaced with underscores}___{solr data type}___{partial or full URI}___{entitiy label}```
This pattern for storing values captures essential information needed for the search query user interface
to present facet-values to users. If we did not store the label, URI, etc. in this way, then display
of each facet value would require a database look-up which would slow down the overall user interface.


### Examples values in dynamic "id" fields:
- `34_catalhoyuk___id___/subjects/E44A115A-DFCB-4971-6750-40955DF2C062___Çatalhöyük`
- `35_proximal_fuseddistal_fused___id___/types/DE9FFE49-B43C-44E6-4BD8-C304012B78FC___Proximal fused/distal fused`
- `periodo_p03wskdm4tb___id___http://n2t.net/ark:/99152/p03wskdm4tb___Early Iron Age Anatolia (1200-700 BC)`
- `123_differentiating_local_from_nonlocal_ceramic_production___id___/projects/81d1157d-28f4-46ff-98dd-94899c1688f8___Differentiating local from nonlocal ceramic production at Late Bronze Age/Iron Age Kinet Höyük using NAA`


### Querying dynamic "id" fields:
Note that entity slug values have their `-` characters replaced by `_` characters. That's because the `-`
character is a special character in solr. Slugs uniquely identify database entities, so we use the slug
values (with `_` to replace `-` characters) in solr filter queries. To do a filter for database entities
in solr, we simply filter for a slug as a prefix, followed by a wild-card character. So a filter for the
"subjects" entity of Çatalhöyük will be: `turkey___context_id:34_catalhoyuk___*`




## Tests and demos:

An important goal of refactoring the search code is to add more confidence that Open Context search
functionality will behave as expected. Therefore, we need to add lots of rigorous unit (tests that
do NOT use the database) and regression (tests that require the database) testing. To invoke tests:

```
# Unit testing of the new search code:
pytest opencontext_py/tests/unit/searcher/new_solrsearcher/ -v

# Regression testing of the new search code:
pytest opencontext_py/tests/regression/searcher/new_solrsearcher/ -v

# Not a pytest test, but a demo over the Web query that responds with a solr-query dictionary:
http://127.0.0.1:8000/query/Turkey%7C%7CItaly?proj=24-murlo||1-domuztepe&q=dog

```

