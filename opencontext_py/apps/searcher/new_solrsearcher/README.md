# README: Refactoring Search

This directory of code had incremental progress on refactoring Open Context's search functionality.

This does nothing to change the existing search features. It is a new project to attempt to make the 
existing convoluted, complicated, obscure and highly redundant code into something that is easier to 
understand and maintain.

A few things to understand first:
- Open Context uses solr dynamic fields to represent project specific attributes
(descriptive properties); projects; spatial contexts; and other metadata.
- Open Context uses "slugs" to identify entities in the database ("LinkedEntities", and
"Manifest" items) for both solr fields and the values in these solr fields.
- The dynamic Solr fields come in two main varieties, with two different purposes. The 
dynamic solr fields that have an "_fq" at the end are meant for filter queries (the "fq"
arguments in a Solr query). The dynamic solr fields that do not have an "_fq" are typically 
used to get facet counts. The dynamic solr fields that end with "_fq" take slugs as values. 
That means they are used for filter queres of entities in the database. The dynaic solr 
fields that don't have "_fq" are often used for getting facet counts. 
