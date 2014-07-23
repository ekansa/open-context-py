import re
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

    def validate_label(self):
        if(len(self.label) > 175):
            self.label = self.label[:172] + '...'
        return self.label

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
        self.label = self.validate_label()
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
        if(raw_slug == '-' or len(raw_slug) < 1):
            raw_slug = 'x'  # slugs are not a dash or are empty
        if(act_proj_short_id is not False):
            raw_slug = str(act_proj_short_id) + '--' + raw_slug
        if(raw_slug[-1:] == '-'):
            raw_slug = raw_slug + 'x'  # slugs don't end with dashes
        raw_slug = re.sub(r'([-]){3,}', r'--', raw_slug)  # slugs can't have more than 2 dash characters
        slug = self.raw_to_final_slug(raw_slug)  # function for making sure unique slugs
        return slug

    def raw_to_final_slug(self, raw_slug):
        """ Converts a raw to a final slug, checks if the slug exists. If it does, add a suffix.
        If the suffixed slug already exists, try the next suffix until we get one that does not exist.
        """
        slug_exists = False
        try:
            slug_exists_res = Manifest.objects.filter(slug=raw_slug)[:1]
            if(len(slug_exists_res) > 0):
                slug_exists = True
            else:
                slug = raw_slug
        except Manifest.DoesNotExist:
            slug_exists = False
            slug = raw_slug
        if slug_exists:
            test_slug = raw_slug
            counter = 0
            while slug_exists:
                slug_count = Manifest.objects.filter(slug__startswith=test_slug).count()
                if(slug_count > 0):
                    test_slug = test_slug + "-" + str(slug_count + counter)  # ok because a slug does not end in a dash
                    counter += 1
                else:
                    slug = test_slug
                    slug_exists = False
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
