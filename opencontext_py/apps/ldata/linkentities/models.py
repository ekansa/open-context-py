import re
from django.db import models
from unidecode import unidecode
from django.template.defaultfilters import slugify


# This class stores linked data annotations made on the data contributed to open context
class LinkEntity(models.Model):
    uri = models.CharField(max_length=200, primary_key=True)
    slug = models.SlugField(max_length=70, unique=True)
    label = models.CharField(max_length=200, db_index=True)
    alt_label = models.CharField(max_length=200, db_index=True)
    vocab_uri = models.CharField(max_length=200)
    ent_type = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    def make_slug(self):
        """
        creates a unique slug for a label with a given type
        """
        le_gen = LinkEntityGeneration()
        slug = le_gen.make_slug(self.uri)
        return slug

    def save(self):
        """
        saves a manifest item with a good slug
        """
        self.slug = self.make_slug()
        super(LinkEntity, self).save()

    class Meta:
        db_table = 'link_entities'


class LinkEntityGeneration():

    def make_slug(self, uri):
        """
        Makes a slug for the URI of the linked entity
        """
        uri_prefixes = {'http://www.cidoc-crm.org/rdfs/cidoc-crm': 'crm-rdf',
                        'http://collection.britishmuseum.org/description/thesauri': 'bm-thes',
                        'http://collection.britishmuseum.org/id/thesauri': 'bm-thes',
                        'http://concordia.atlantides.org': 'concordia',
                        'http://gawd.atlantides.org/terms': 'gawd',
                        'http://purl.org/dc/terms': 'dc-terms',
                        'http://dbpedia.org/resource': 'dbpedia',
                        'http://dbpedia.org/resource': 'dbpedia',
                        'http://eol.org/pages': 'eol-p',
                        'http://opencontext.org/vocabularies/dinaa': 'dinaa',
                        'http://opencontext.org/vocabularies/oc-general': 'oc-gen',
                        'http://opencontext.org/vocabularies/open-context-zooarch': 'oc-zoo',
                        'http://orcid.org': 'orcid',
                        'http://pleiades.stoa.org/places': 'pleiades-p',
                        '"http://pleiades.stoa.org/vocabularies/time-periods': 'pleiades-tp',
                        'http://purl.obolibrary.org/obo': 'obo',
                        'http://purl.org/NET/biol/ns': 'biol',
                        'http://sw.opencyc.org': 'opencyc',
                        'http://www.freebase.com/view/en': 'freebase',
                        'http://en.wiktionary.org/wiki': 'wiktionary',
                        'http://www.geonames.org': 'geonames',
                        'http://www.w3.org/2000/01/rdf-schema': 'rdfs',
                        'http://www.w3.org/2003/01/geo/wgs84_pos': 'geo',
                        'http://www.w3.org/2004/02/skos/core': 'skos',
                        'http://en.wikipedia.org/wiki': 'wiki',
                        'http://id.loc.gov/authorities/subjects': 'loc-sh'
                        }
        for uri_root, uri_prefix in uri_prefixes.items():
            uri = uri.replace(uri_root, uri_prefix)
            #  replaces the start of a uri with a prefix
        uri = uri.replace('https://', '')
        uri = uri.replace('http://', '')
        uri = uri.replace('/', '-')
        uri = uri.replace('.', '-')
        uri = uri.replace('#', '-')
        uri = uri.replace('_', ' ')
        raw_slug = slugify(unidecode(uri[:55]))
        raw_slug = raw_slug.replace('---', '--')  # make sure no triple dashes, conflicts with solr
        if(raw_slug[-1:] == '-'):
            raw_slug = raw_slug[:-1]
        if(raw_slug[-1:] == '-'):
            raw_slug = raw_slug + 'x'  # slugs don't end with dashes
        raw_slug = re.sub(r'([-]){3,}', r'--', raw_slug)  # slugs can't have more than 3 dash characters
        slug = raw_slug
        try:
            slug_in = LinkEntity.objects.get(slug=raw_slug)
            slug_exists = True
        except LinkEntity.DoesNotExist:
            slug_exists = False
        if(slug_exists):
            try:
                slug_count = LinkEntity.objects.filter(slug__startswith=raw_slug).count()
            except LinkEntity.DoesNotExist:
                slug_count = 0
            if(slug_count > 0):
                slug = raw_slug + "-" + str(slug_count + 1)  # ok because a slug does not end in a dash
        return slug

    def fix_blank_slugs(self):
        """
        assigns slugs to linked entities
        """
        cc = 0
        try:
            no_slugs = LinkEntity.objects.all().exclude(slug__isnull=False)
        except LinkEntity.DoesNotExist:
            no_slugs = False
        if(no_slugs is not False):
            for nslug in no_slugs:
                nslug.save()
                cc += 1
        return cc
