import re
import reversion  # version control object
import collections
from jsonfield import JSONField  # json field for complex objects
from django.db import models
from unidecode import unidecode
from django.template.defaultfilters import slugify


# This class stores linked data annotations made on the data contributed to open context
@reversion.register  # records in this model under version control
class LinkEntity(models.Model):
    uri = models.CharField(max_length=200, primary_key=True)
    slug = models.SlugField(max_length=70, unique=True)
    label = models.CharField(max_length=200, db_index=True)
    alt_label = models.CharField(max_length=200, db_index=True)
    sort = models.CharField(max_length=60, db_index=True)
    vocab_uri = models.CharField(max_length=200)
    ent_type = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)
    localized_json = JSONField(default={},
                               load_kwargs={'object_pairs_hook': collections.OrderedDict},
                               blank=True)

    def clean_uri(self, uri):
        """
        cleans a uri to remove cruft that's not part of the identifier
        """
        le_gen = LinkEntityGeneration()
        uri = le_gen.make_clean_uri(uri)
        return uri

    def make_slug(self):
        """
        creates a unique slug for a label with a given type
        """
        le_gen = LinkEntityGeneration()
        slug = le_gen.make_slug(self.uri)
        return slug

    def save(self, *args, **kwargs):
        """
        saves a manifest item with a good slug
        """
        self.uri = self.clean_uri(self.uri)
        if self.slug is None:
            self.slug = self.make_slug()
        elif self.slug == '':
            self.slug = self.make_slug()
        if self.sort is None:
            self.sort = ''
        self.sort = self.sort[:60]
        # print('Type: ' + self.ent_type + ' ' + str(len(self.ent_type)))
        # print('URI: ' + self.uri + ' ' + str(len(self.uri)))
        # print('Slug: ' + self.slug + ' ' + str(len(self.slug)))
        # print('Sort: ' + self.sort + ' ' + str(len(self.sort)))
        super(LinkEntity, self).save(*args, **kwargs)

    class Meta:
        db_table = 'link_entities'


class LinkEntityGeneration():

    # URIs that end in a numeric value
    NUMERIC_URI_PREFIXES = ['http://pleiades.stoa.org/places/',
                            'http://eol.org/pages/',
                            'http://www.geonames.org/']

    USE_HTTPS_PARTS = []

    def make_clean_uri(self, uri, http_default=True):
        """
        Makes a numeric uri for certain vocabularies
        by stripping off extra slashes and other crud
        """
        uri = uri.strip()
        uri = uri.replace('.html', '')  # strip off .html since it's not a URI part
        if http_default:
            # default all to be not-https for uris for now
            uri = uri.replace('https://', 'http://')
        if len(self.USE_HTTPS_PARTS) > 0:
            for http_part in self.USE_HTTPS_PARTS:
                if http_part in uri and 'http://' in uri:
                    # can have a list of URI parts that we allow HTTPS
                    uri = uri.replace('http://', 'https://')
        for prefix in self.NUMERIC_URI_PREFIXES:
            if prefix in uri:
                part_uri = uri.replace(prefix, '')
                if '/' in part_uri:
                    part_ex = part_uri.split('/')
                    uri = prefix + part_ex[0].strip()
                else:
                    uri = prefix + part_uri.strip()
        return uri

    def make_slug(self, uri):
        """
        Makes a slug for the URI of the linked entity
        """
        actual_uri = uri
        uri_prefixes = {'http://www.cidoc-crm.org/rdfs/cidoc-crm': 'crm-rdf',
                        'http://erlangen-crm.org/current': 'cidoc-crm',
                        'http://collection.britishmuseum.org/description/thesauri': 'bm-thes',
                        'http://collection.britishmuseum.org/id/thesauri': 'bm-thes',
                        'http://concordia.atlantides.org': 'concordia',
                        'http://gawd.atlantides.org/terms': 'gawd',
                        'http://purl.org/dc/terms': 'dc-terms',
                        'http://dbpedia.org/resource': 'dbpedia',
                        'http://www.wikidata.org/wiki': 'wikidata',
                        'http://eol.org/pages': 'eol-p',
                        'http://opencontext.org/vocabularies/dinaa': 'dinaa',
                        'http://opencontext.org/vocabularies/oc-general': 'oc-gen',
                        'http://opencontext.org/vocabularies/open-context-zooarch': 'oc-zoo',
                        'http://orcid.org': 'orcid',
                        'http://pleiades.stoa.org/places': 'pleiades-p',
                        'http://pleiades.stoa.org/vocabularies/time-periods': 'pleiades-tp',
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
                        'http://id.loc.gov/authorities/subjects': 'loc-sh',
                        'http://core.tdar.org/browse/site-name': 'tdar-kw-site',
                        'http://purl.org/ontology/bibo': 'bibo',
                        'http://creativecommons.org/ns#': 'cc',
                        'http://www.w3.org/2002/07/owl#': 'owl',
                        'http://creativecommons.org/licenses': 'cc-license',
                        'http://creativecommons.org/publicdomain': 'cc-publicdomain',
                        'http://n2t.net/ark:/99152/p0': 'periodo-p0',
                        'http://vocab.getty.edu/aat': 'getty-aat',
                        'http://nomisma.org/ontology': 'nmo',
                        'http://numismatics.org/ocre/id': 'ocre',
                        'http://portal.vertnet.org': 'vertnet-rec',
                        'http://vocab.getty.edu/tgn': 'getty-tgn',
                        'http://purl.org/heritagedata/schemes/mda_obj/concepts': 'fish',
                        'http://arachne.dainst.org/search': 'arachne-search',
                        'http://arachne.dainst.org/entity/': 'arachne-ent',
                        'http://www.jstor.org/journal': 'jstor-jrn',
                        'http://www.jstor.org/stable': 'jstor',
                        'http://scholarworks.sfasu.edu/ita': 'i-texas-a',
                        'http://doi.org': 'doi',
                        'https://doi.org': 'doi'
                        }
        for uri_root, uri_prefix in uri_prefixes.items():
            #  replaces the start of a uri with a prefix
            uri = uri.replace(uri_root, uri_prefix)
        uri = uri.replace('https://www.', '')
        uri = uri.replace('http://www.', '')
        uri = uri.replace('https://', '')
        uri = uri.replace('http://', '')
        uri = uri.replace('/', '-')
        uri = uri.replace('.', '-')
        uri = uri.replace('#', '-')
        uri = uri.replace('%20', '-')
        uri = uri.replace('q=', '-')
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
            if slug_in.uri != actual_uri:
                slug_exists = True
            else:
                slug_exists = False
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

    def check_add_common_entities(self):
        """ checks and adds common entities to the database """
        self.check_add_owlsameas_pred()
        self.check_add_ispartof_pred()
        self.check_add_haspart_pred()
        self.check_add_period_pred()

    def check_add_owlsameas_pred(self):
        """ Adds dublin core temporal if it doesn't exist yet
        """
        pred_uri = 'http://www.w3.org/2002/07/owl#sameAs'
        lev = LinkEntity.objects.filter(uri=pred_uri)[:1]
        if len(lev) < 1:
            le = LinkEntity()
            le.uri = pred_uri
            le.label = 'Same As'
            le.alt_label = 'Same As'
            le.vocab_uri = 'http://www.w3.org/2002/07/owl'
            le.ent_type = 'property'
            le.save()

    def check_add_ispartof_pred(self):
        """ Adds dublin core temporal if it doesn't exist yet
        """
        pred_uri = 'http://purl.org/dc/terms/isPartOf'
        lev = LinkEntity.objects.filter(uri=pred_uri)[:1]
        if len(lev) < 1:
            le = LinkEntity()
            le.uri = pred_uri
            le.label = 'Is Part Of'
            le.alt_label = 'Is Part Of'
            le.vocab_uri = 'http://purl.org/dc/terms'
            le.ent_type = 'property'
            le.save()

    def check_add_haspart_pred(self):
        """ Adds dublin core temporal if it doesn't exist yet
        """
        pred_uri = 'http://purl.org/dc/terms/hasPart'
        lev = LinkEntity.objects.filter(uri=pred_uri)[:1]
        if len(lev) < 1:
            le = LinkEntity()
            le.uri = pred_uri
            le.label = 'Has Part'
            le.alt_label = 'Has Part'
            le.vocab_uri = 'http://purl.org/dc/terms'
            le.ent_type = 'property'
            le.save()

    def check_add_period_pred(self):
        """ Adds dublin core temporal if it doesn't exist yet
        """
        temporal_pred = 'http://purl.org/dc/terms/temporal'
        lev = LinkEntity.objects.filter(uri=temporal_pred)[:1]
        if len(lev) < 1:
            le = LinkEntity()
            le.uri = temporal_pred
            le.label = 'Temporal Coverage'
            le.alt_label = 'Temporal Coverage'
            le.vocab_uri = 'http://purl.org/dc/terms'
            le.ent_type = 'property'
            le.save()

    def check_add_note_pred(self):
        """ Adds dublin core temporal if it doesn't exist yet
        """
        pred = 'http://opencontext.org/vocabularies/oc-general/has-note'
        lev = LinkEntity.objects.filter(uri=pred)[:1]
        if len(lev) < 1:
            le = LinkEntity()
            le.uri = pred
            le.label = 'Has note'
            le.alt_label = 'Has note'
            le.vocab_uri = 'http://opencontext.org/vocabularies/oc-general/'
            le.ent_type = 'property'
            le.save()
