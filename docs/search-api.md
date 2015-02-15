Open Context Search / Query API
=======================


PART 1. GENERAL POINTS
------------------------------------------

(1.1) Faceted Search / Browse:

The general goal of the search/query/faceted-browse API is to provide clients with links
described with useful information to:

  1. Change state (further filter Open Context)
  2. Get useful numeric summaries of filtered sets of Open Context records
  
This is all built on a model of faceted search / faceted browsing. In faceted search, the
service returns information that summarizes a collection according to different metadata
facets. This is the main way data in Open Context can be understood in aggregate.


(1.2) JSON-LD: 

In order to make the faceted search information more intelligible and hopefully
more widely useful, Open Context returns faceted search results as JSON-LD. JSON-LD is
a W3C standard for expressing "linked-data", where Web-URIs identify concepts and entities.
Open Context uses JSON-LD because it helps add some precision to semantics without requiring
clients to adopt still somewhat arcane "Semantic Web" technologies. You can use JSON-LD to
get RDF triples if you like, or you can do what we do internally in Open Context and just
use it as plain JSON like other mere mortals.


(1.3) GeoJSON(-LD):

This aspect is still in development, but the JSON-LD results will also be valid GeoJSON, meaning
that GeoJSON clients can use the data without fuss. Of course, there will be lots in the service
that your standard GeoJSON client ignores, but that's another issue.



PART 2. BEHIND THE SCENES
------------------------------------------

(2.1) General Architecture:

The JSON-LD faceted search service exposes to the Web data assembled in a hopefull nicely packaged
and easy to follow manner for clients. It tries to provide lots of links and information on what
the links mean so that a client can navigate the API without requiring (much) knowledge about 
Open Context's data schemas or back-end sofware (especially Apache Solr). 


(2.2) Indexing and Querying:

Open Context uses a Postgres data store. The Python application queries the Postgres databaase to
generate JSON-LD representations for each "item" (the minimal entities assigned URIs by Open Context).
These items are indexed by Apache-Solr. The Python application passes requests from the Web to Solr,
then packages results from Solr into JSON-LD for consumtion by Web clients. Behind Open Context's 
faceted search service data flows through the following steps:

  2.2.a Expression as GeoJSON-LD. Each individual record in Open Context has a JSON-LD expression.
  
  2.2.b Mapping of the item JSON-LD record to a Solr document conforming to Open Context's Solr schema.
  Relevant code and configurations are here:
  
  2.2.b.1 Solr Schema:
  
        /open-context-py/solr-config/schema.xml
  
  2.2.b.2 Python code to generate a Solr document from an item JSON-LD:
  
        /open-context-py/opencontext_py/apps/indexer/solrdocument.py
  
  2.2.b Apache Solr indexes data in the Solr documents. The Solr documents have a somewhat more simplified
  data model than Open Context's JSON-LD representations, since modeling nuances are not necessarily
  needed for most use-cases.
  
  2.2.c With the data indexed by Solr, the Open Context application can then get requests from the Web. The
  Python application translates requests parameters sent by Web clients to formulate queries to Solr.
  Relevant code is here:
  
        /open-context-py/opencontext_py/apps/searcher/solrsearcher/models.py
        /open-context-py/opencontext_py/apps/searcher/solrsearcher/querymaker.py
  
  2.2.d Solr responds to queries by returning a JSON document. By itself Solr's JSON results are not that 
  easy to understand or navigate. So, the Open Context application uses Solr's results to generate an easier
  to navigate JSON-LD document. Relevant code is here:
  
        /open-context-py/opencontext_py/apps/searcher/solrsearcher/makejsonld.py
        /open-context-py/opencontext_py/apps/searcher/solrsearcher/filterlinks.py



PART 3. ADDITIONAL QUERYING GUIDES
------------------------------------------

(3.1) Full-text Searches:

The Open Context search service provides links with a "template" guide on how to request full-text
searches. Certain URLs have {SearchTerm} (not URL escaped) where a client needs to insert URL escaped
text for keyword searches. The JSON example below illustrates key-word search templating:

      "oc-api:has-text-search": [
        {
            "id": "#textfield-keyword-search", 
            "label": "General Keyword Search", 
            "oc-api:search-term": null, 
            "oc-api:template": "http://opencontext.org/sets/?q={SearchTerm}", 
            "oc-api:template-json": "http://opencontext.org/sets/.json?q={SearchTerm}"
        }
      ] 


(3.2) Numeric and Date Searches:

Open Context will make "range-facets" for numeric and date fields. These range facets also serve as
a template to pass query expressions (using Solr's syntax) to use with numeric or date fields
exposed by Open Context's search service. Here's an example:


      "oc-api:has-range-options": [
        {
          "id": "http://opencontext.org/sets/Italy?proj=24-murlo&prop=24-sd---%5B3.5+TO+7.24+%5D", 
          "json": "http://opencontext.org/sets/Italy.json?proj=24-murlo&prop=24-sd---%5B3.5+TO+7.24+%5D", 
          "label": "3.5", 
          "count": 31, 
          "oc-api:min": 3.5, 
          "oc-api:max": 7.24
        }, 




  
  

