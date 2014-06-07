from django.db import models
from unidecode import unidecode
from django.template.defaultfilters import slugify


# This class stores linked data annotations made on the data contributed to open context
class LinkEntity(models.Model):
    uri = models.CharField(max_length=200, primary_key=True)
    slug = models.SlugField(max_length=70, blank=True, null=True, db_index=True)
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
        uri = uri.replace('https://', '')
        uri = uri.replace('http://', '')
        uri = uri.replace('/', '-')
        uri = uri.replace('.', '-')
        uri = uri.replace('_', ' ')
        raw_slug = slugify(unidecode(uri[:55]))
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
                slug = raw_slug + "-" + str(slug_count + 1)
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
