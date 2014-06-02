from unidecode import unidecode
from django.utils import timezone
from django.db import models
from django.template.defaultfilters import slugify
from opencontext_py.apps.ocitems.projects.models import Project as Project


# Manifest provides basic item metadata for all open context items that get a URI
class Manifest(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    repo = models.CharField(max_length=200)
    class_uri = models.CharField(max_length=200)
    slug = models.SlugField(max_length=70, blank=True, null=True, db_index=True)
    label = models.CharField(max_length=200)
    des_predicate_uuid = models.CharField(max_length=50)
    views = models.IntegerField()
    indexed = models.DateTimeField(blank=True, null=True)
    vcontrol = models.DateTimeField(blank=True, null=True)
    archived = models.DateTimeField(blank=True, null=True)
    published = models.DateTimeField(db_index=True)
    revised = models.DateTimeField(db_index=True)
    record_updated = models.DateTimeField(auto_now=True)

    def make_slug(self):
        """
        creates a unique slug for a label with a given type
        """
        man_gen = ManifestGeneration()
        slug = man_gen.make_manifest_slug(self.label, self.item_type, self.project_uuid)
        return slug

    def save(self):
        """
        saves a manifest item with a good slug
        """
        self.slug = self.make_slug()
        super(Manifest, self).save()

    class Meta:
        db_table = 'oc_manifest'
        unique_together = (("item_type", "slug"),)


class ManifestGeneration():

    def make_manifest_slug(self, label, item_type, project_uuid):
        """
        gets the most recently updated Subject date
        """
        label = label.replace('_', ' ')
        raw_slug = slugify(unidecode(label[:55]))
        act_proj_short_id = False
        if(project_uuid != '0'):
            try:
                act_proj = Project.objects.get(uuid=project_uuid)
                act_proj_short_id = act_proj.short_id
            except Project.DoesNotExist:
                act_proj_short_id = False
        if(act_proj_short_id is not False):
            raw_slug = raw_slug + '--' + str(act_proj_short_id)
        slug = raw_slug
        try:
            slug_in = Manifest.objects.get(slug=raw_slug)
            slug_exists = True
        except Manifest.DoesNotExist:
            slug_exists = False
        if(slug_exists):
            try:
                slug_count = Manifest.objects.filter(slug__startswith=raw_slug).count()
            except Manifest.DoesNotExist:
                slug_count = 0
            if(slug_count > 0):
                slug = raw_slug + "-" + str(slug_count + 1)
        return slug

    def fix_blank_slugs(self):
        cc = 0
        try:
            no_slugs = Manifest.objects.all().exclude(slug__isnull=False)
        except Manifest.DoesNotExist:
            no_slugs = False
        if(no_slugs is not False):
            for nslug in no_slugs:
                nslug.save()
                cc += 1
        return cc
