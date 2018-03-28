OPEN CONTEXT AND CROSS-DOMAIN DEPLOYMENT
========================================

Open Context will often publish media resources that can be viewed in a Web broweser via different Javascript tools.
Such files include:
  1. PDF, viewed with OpenSeaDragon / Viewer.js
  2. NEXUS (.nxs) 3D models, viewed with 3DHOP tools

## CORS AND PROXY REQUESTS
In our current deployment however, the domain 'https://opencontext.org/' does not actually store most of the media files.
The files are stored on other servers with other domains, which introduces some CORS concerns.
The "change-secrets.json" (deployed as "secrets.json") has an key called "CORS_OK_DOMAINS" that will accept a list of domains
that you can use to store media files for CORS requests. If a URL to a media file is in a listed CORS_OK_DOMAIN, then requests
will be made directly to that server to get a given media file. If not, then Open Context modifiles the media file URL to proxy
the request to Open Context. This obviously reduces speed and performance, but it avoids CORS problems. 

*Please note* that requests to NEXUS 3D files will NOT work via a proxy. You must put such files on the same domain hosting your
instance of Open Context or put them on a server that allows CORS.

To help configure a server for media files, hre are CORS configurations for Apache (.htaccess) that seem to work:

    Header always set Access-Control-Allow-Headers "Overwrite, Destination, Content-Type, Depth, User-Agent, Translate, Range, Content-Range, Timeout, X-File-Size, X-Requested-With, If-Modified-Since, X-File-Name, Cache-Control, Location, Lock-Token, If"
    Header always set Access-Control-Allow-Methods "ACL, CANCELUPLOAD, CHECKIN, CHECKOUT, COPY, DELETE, GET, HEAD, LOCK, MKCALENDAR, MKCOL, MOVE, OPTIONS, POST, PROPFIND, PROPPATCH, PUT, REPORT, SEARCH, UNCHECKOUT, UNLOCK, UPDATE, VERSION-CONTROL"
    Header always set Access-Control-Expose-Headers "DAV, content-length, Allow" 
