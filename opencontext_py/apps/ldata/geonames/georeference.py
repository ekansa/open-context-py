import sys
import json
from time import sleep
from opencontext_py.apps.ldata.geonames.api import GeonamesAPI
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.geospace.models import Geospace


class GeoReference():
    """ methods to add geospatial data to Open Context items
        associated with Geonames
    """

    def __init__(self):
        self.request_error = False
        self.new_geodata = 0
        self.overwrite = False
        self.specifity = 0

    def add_geonames_data_via_annotations(self, project_uuids=False):
        """ Adds geonames spatial data for items with geonames annotations """
        geo_related = self.get_items_with_geoname_annotations(project_uuids)
        for uuid, geonames_uri in geo_related.items():
            if self.overwrite:
                Geospace.objects.filter(uuid=uuid).delete()
            geo_feature = Geospace.objects.filter(uuid=uuid).first()
            if geo_feature is not None and geo_feature.latitude == 0 and geo_feature.longitude == 0:
                Geospace.objects.filter(
                    uuid=uuid,
                    latitude=0,
                    longitude=0,
                ).delete()
                geo_feature = None
            # print(str(len(geo_features)) + ' features in: ' + uuid + ' with: ' + geonames_uri)
            if geo_feature:
                # Skip, since we already have geofeatres for this item.
                continue
            manifest = Manifest.objects.filter(uuid=uuid).first()
            if not manifest:
                print('Cannot find manifest record for: {} {}'.format(uuid, geonames_uri))
                continue
            # No geospatial data exists for this item yet, so go fetch from GeoNames
            geoapi = GeonamesAPI()
            json_data = geoapi.get_json_for_geonames_uri(geonames_uri)
            if not isinstance(json_data, dict):
                self.request_error = True
                print('Problem with: ' + geoapi.request_url + ' from: ' + geonames_uri)
                continue
            ok = self.create_geospatial_data_from_geonames_json(manifest, json_data)

    def create_geospatial_data_from_geonames_json(self, manifest, json_data):
        """ creates and saves geospatial data derived from geonames """
        ok = False
        coords = ''
        lat = False
        lon = False
        ftype = 'Point'
        if 'bbox' in json_data:
            ftype = 'Polygon'
            east = json_data['bbox']['east']
            south = json_data['bbox']['south']
            west = json_data['bbox']['west']
            north = json_data['bbox']['north']
            lat = (south + north) / 2
            lon = (east + west) / 2
            coordinates = []
            cood_inner = []
            cood_inner.append([east,
                               south])
            cood_inner.append([east,
                               north])
            cood_inner.append([west,
                               north])
            cood_inner.append([west,
                               south])
            cood_inner.append([east,
                               south])
            coordinates.append(cood_inner)
            coords = json.dumps(coordinates,
                                indent=4,
                                ensure_ascii=False)
        else:
            coords = ''
            if 'lat' in json_data:
                lat = float(json_data['lat'])
            if 'lng' in json_data:
                lon = float(json_data['lng'])
        if lat is not False and lon is not False:
            # we have OK coodinates, let's save them
            geodata = Geospace()
            geodata.uuid = manifest.uuid
            geodata.project_uuid = manifest.project_uuid
            geodata.source_id = 'geonames-api'
            geodata.item_type = manifest.item_type
            geodata.feature_id = 1
            geodata.meta_type = 'oc-gen:discovey-location'
            geodata.ftype = ftype
            geodata.latitude = lat
            geodata.longitude = lon
            geodata.specificity = self.specifity
            geodata.coordinates = coords
            geodata.note = 'Location data from GeoNames.org'
            geodata.save()
            ok = True
        if ok:
            self.new_geodata += 1
            output = 'New geodata [' + str(self.new_geodata) + '] ' + str(manifest.label)
            output += ' (' + str(manifest.uuid) + ')'
            print(output)
        return ok

    def get_items_with_geoname_annotations(self, project_uuids=False):
        """ gets items with geoname annotations """
        geo_related = {}
        anno_list = self.get_geoname_annotations(project_uuids)
        for geo_anno in anno_list:
            if geo_anno.subject_type == 'subjects':
                # the geonames annotation applies directly to a subjects item
                if geo_anno.subject not in geo_related:
                    geo_related[geo_anno.subject] = geo_anno.object_uri
            elif geo_anno.subject_type == 'types':
                # the geonames annotation is asserted on a type. to get the
                # subjects item used with this type, we need to do a lookup
                # on the assertions table
                assertions = Assertion.objects\
                                      .filter(object_uuid=geo_anno.subject)
                for geo_ass in assertions:
                    if geo_ass.uuid not in geo_related:
                        geo_related[geo_ass.uuid] = geo_anno.object_uri
        return geo_related

    def get_geoname_annotations(self, project_uuids=False):
        """ gets geoname annotations, with optional
            filter constraint of a project list
        """
        if project_uuids is not False:
            if not isinstance(project_uuids, list):
                project_uuids = [project_uuids]
            anno_list = LinkAnnotation.objects\
                                      .filter(project_uuid__in=project_uuids,
                                              object_uri__icontains='geonames.org')
        else:
            anno_list = LinkAnnotation.objects\
                                      .filter(object_uri__icontains='geonames.org')
        return anno_list

