Directions for Deploying Solr for Open Context via Docker
=======================


PART 1. SETTING UP SOLR (8.9) WITH DOCKER
------------------------------------------
(1.1) These directions are for installing and deploying a Solr index for
Open Context on a Linux server. You may need to adapt these directions for
installation on a different OS. The directions assume that you already have
Docker installed and running on your server. To activate Docker on your server, you can use a command like:

`sudo dockerd`


(1.2) Solr makes Docker images available on Docker hub (see: [https://hub.docker.com/_/solr/](https://hub.docker.com/_/solr/) ).

(1.3) Make a directory to store your Solr data (index) that is outside of
the container. This will let it persist if you need to restart the container.

```

# Make your Solr Open Context data directory:
mkdir solr-oc-data

# Make sure that Solr running on Docker will have needed ownership
sudo chown 8983:8983 solr-oc-data

# Do the initial setup of the Open Context solr collection
# and data directories. This should persist after you turn off
# the Solr Docker container.
sudo docker run -d -v "$PWD/solr-oc-data:/var/solr" -p 8983:8983 --name oc_solr solr solr-precreate open-context

# Turn off the Docker instance
sudo docker stop oc_solr

# Copy the Solr schema to the appropriate place in the persistent
# solr data directory, add permissions
export PATH_TO_SOLR_CONF=~/github/open-context-py/solr-config/Solr-9/
sudo cp $PATH_TO_SOLR_CONF/schema.xml solr-oc-data/data/open-context/conf/managed-schema
sudo cp $PATH_TO_SOLR_CONF/schema.xml solr-oc-data/data/open-context/conf/schema.xml
sudo cp $PATH_TO_SOLR_CONF/currency.xml solr-oc-data/data/open-context/conf/currency.xml
sudo cp $PATH_TO_SOLR_CONF/solrconfig.xml solr-oc-data/data/open-context/conf/solrconfig.xml
sudo chown -R 8983:8983 solr-oc-data

# Remove the stopped Docker containers so we can reuse this
# directory
sudo docker system prune

# Restart the Solr Docker instance
sudo docker run -d -v "$PWD/solr-oc-data:/var/solr" -p 8983:8983 --name oc_solr solr
