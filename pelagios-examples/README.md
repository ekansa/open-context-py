Pelagios Examples
===============

Open Context Pelagios Support

This directory contains sample outputs from Open Context to express how Open Context data
relates to place entities in Web gazetteers using the "recipes" promoted by the Pelagios
project (https://github.com/pelagios/pelagios-cookbook/wiki/Joining-Pelagios).

Currently, this directory only includes test/draft outputs of open annoation assertions expressed in the Turtle format. The directory also now includes a test/draft VOID file also required by Pelagios. On Open Context, the void file can be requested at:
http://opencontext.org/pelagios/void

In addition, some Open Context data can be used as gazetteer data, especially site file records published
with the Digital Index of North American Archaeology (DINAA) project. We will consult with the Pelagios
team to make sure these data meet Pelagios requirements for gazetteers.


NOTES ABOUT THE OPEN ANNOTATION ASSERTIONS
------------------------------------------
Open Context publishes a lot of data, but only a few records directly relate to place entities in gazetteers. I've been working on ways to show a summary of resources relevant to gazetteer identified places, but related through containment relationships. For instance, I want use the Pelagios annotations to show that Open Context may have coin, animal bone, object (etc), data records and images that come from a site that has a gazetteer reference, even if the animal bones (coins, objects, etc) themselves do not directly link to a place in a gazetteer.

The draft Turtle file attempts to meet the above requirements. Notice that some of the annotated resources are not really proper stable URIs but are URLs to search results of relevant sets of materials. Is this an acceptable strategy or should Open Context mint more stable URIs for these different sets of search results? If so, we may need to do a temporary redirect to the query URL if someone tries to resolve a stable URI that points to a search result set, rather than a single record.

The other matter centers on choosing a vocabulary to explicitly note "coin", "animal bone", "pottery" etc. Should we use dcterms:subject to indicate type / classification information for these data records? If so, would people prefer us to use the Getty AAT or another vocabulary like the LoC subjects headings? Thoughts?


