import json
import hashlib
try:
    from shapely.geometry import shape, mapping
except:
    pass  # just to get this in production
import reversion  # version control object
from collections import OrderedDict
from django.db import models


# Geodata provides geospatial feature data for an item. These get used through spatial
# inheritance for items without their own geospatial data.
@reversion.register  # records in this model under version control
class Geospace(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50, db_index=True)
    feature_id = models.IntegerField()
    meta_type = models.CharField(max_length=50)
    ftype = models.CharField(max_length=200, db_index=True)
    latitude = models.DecimalField(max_digits=24, decimal_places=21)
    longitude = models.DecimalField(max_digits=24, decimal_places=21)
    specificity = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)
    coordinates = models.TextField()
    note = models.TextField()

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids and location types
        """
        hash_obj = hashlib.sha1()
        concat_string = self.uuid + " " + str(self.meta_type) + " " + str(self.feature_id)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(Geospace, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_geospace'


class GeospaceGeneration():
    """ methods for managing geospatial classes

       at the moment, this chiefly generates a centroid
       for coordinates.

from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration
from opencontext_py.apps.imports.records.models import ImportCell
geo_rec = ImportCell.objects.get(rec_hash='dff753b2b2b6967ebcb3b6925aab1182e346b0ce')
gg = GeospaceGeneration()
gg.make_centroid(geo_rec.record)
geo_row = Geospace.objects.get(hash_id='ee51372c66a553195e8647cd0720e20e8a632f98')
gg.get_centroid_lonlat_coordinates(geo_row.coordinates, geo_row.ftype)

    """

    def __init__(self):
        pass

    def get_centroid_lonlat_coordinates(self, geojson_geometry_str, geom_type='Polygon'):
        """ returns a list of the centroid lon / lat coordinates
            yes, in that GeoJSON coordinate order
        """
        lon_lat = False
        centroid = self.make_centroid(geojson_geometry_str, geom_type)
        if isinstance(centroid, dict):
            if 'coordinates' in centroid:
                lon_lat = centroid['coordinates']  # this is a tuple that's created
        return lon_lat

    def make_centroid(self, geojson_geometry_str, geom_type='Polygon'):
        """ converts a geojson geojson_geometry_string
            OR a coordinate string into
            a centroid
        """
        centroid = False
        geojson_geom = False
        try:
            json_obj = json.loads(geojson_geometry_str)
        except:
            json_obj = False
        if isinstance(json_obj, list):
            geojson_geom = {'type': geom_type}
            geojson_geom['coordinates'] = json_obj
        elif isinstance(json_obj, dict):
            if 'type' in json_obj \
               and 'coordinates' in json_obj:
                geojson_geom = json_obj
            elif 'coordinates' in json_obj:
                geojson_geom = json_obj
                geojson_geom['type'] = geom_type
        else:
            geojson_geom = False
        if isinstance(geojson_geom, dict):
            geom = shape(geojson_geom)
            g_centroid = geom.centroid
            centroid = mapping(g_centroid)
        return centroid