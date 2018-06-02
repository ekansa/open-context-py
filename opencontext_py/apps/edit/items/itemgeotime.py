import time
import datetime
import json
from dateutil.parser import parse
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.cache import cache
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.validategeojson import ValidateGeoJson
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.versioning.deletion import DeletionRevision
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.projects.metadata import ProjectMeta, ProjectRels


class ItemGeoTime():
    """ This class contains methods
        creating, editing, and deleting
        assertions
    """

    def __init__(self,
                 uuid,
                 request=False):
        self.uuid = uuid
        self.creator_uuid = False
        self.request = request
        self.errors = {'uuid': False,
                       'html': False}
        self.response = {}
        if uuid is not False:
            try:
                self.manifest = Manifest.objects.get(uuid=uuid)
            except Manifest.DoesNotExist:
                self.manifest = False
                self.errors['uuid'] = 'Item ' + uuid + ' not in manifest'
            if request is not False and self.manifest is not False:
                # check to make sure edit permissions OK
                pp = ProjectPermissions(self.manifest.project_uuid)
                self.edit_permitted = pp.edit_allowed(request)
            else:
                # default to no editting permissions
                self.edit_permitted = False

    def add_update_geo_data(self, post_data):
        """ Updates a file associated with a media item """
        ok = True
        errors = []
        note = ''
        required_params = ['source_id',
                           'hash_id',
                           'meta_type',
                           'ftype',
                           'feature_id',
                           'latitude',
                           'longitude',
                           'specificity',
                           'geojson']
        for r_param in required_params:
            if r_param not in post_data:
                # we're missing some required data
                # don't create the item
                ok = False
                message = 'Missing paramater: ' + r_param + ''
                errors.append(message)
                note = '; '.join(errors)
        if ok:
            coordinates = ''
            hash_id = post_data['hash_id'].strip()
            if len(hash_id) < 1:
                hash_id = False
            source_id = post_data['source_id'].strip()
            ftype = post_data['ftype'].strip()
            # validate the dates
            output = self.validate_float_param('latitude', post_data, errors)
            latitude = output['float']
            errors = output['errors']
            output = self.validate_float_param('longitude', post_data, errors)
            longitude = output['float']
            errors = output['errors']
            output = self.validate_int_param('feature_id', post_data, errors)
            feature_id = output['integer']
            errors = output['errors']
            output = self.validate_int_param('specificity', post_data, errors)
            specificity = output['integer']
            errors = output['errors']
            # now check for GeoJSON, and validate if added
            coordinates = ''
            geojson_str = post_data['geojson'].strip()
            if len(geojson_str) > 1:
                # we have a geojson object
                output = self.validate_geojson(geojson_str, errors)
                coordinates = output['coordinates']
                if output['type'] is not False:
                    ftype = output['type']
                    if isinstance(coordinates, str):
                        v_geojson = ValidateGeoJson()
                        coord_list = json.loads(coordinates)
                        coord_list  = v_geojson.fix_geometry_rings_dir(ftype, coord_list )
                        coordinates = json.dumps(coord_list)
                        gg = GeospaceGeneration()
                        lon_lat = gg.get_centroid_lonlat_coordinates(coordinates, ftype)
                        latitude = lon_lat[1]
                        longitude = lon_lat[0]
                if coordinates is False and latitude is not False\
                   and longitude is not False:
                    # no coordinates input in GeoJSON so make them
                    ftype = 'Point'
                    coordinates = json.dumps([longitude, latitude],
                                             indent=4,
                                             ensure_ascii=False)
            if latitude is False or longitude is False \
               or feature_id is False or coordinates is False \
               or specificity is False:
                # 1 or more of the geospatial data are bad
                ok = False
                note = '; '.join(errors)
            else:
                act_geo = None
                if hash_id is not False:
                    try:
                        act_geo = Geospace.objects.get(hash_id=hash_id)
                    except Geospace.DoesNotExist:
                        act_geo = False
                        ok = False
                        message = 'Cannot find geo record for hash_id: ' + str(hash_id)
                        errors.append(message)
                        note = '; '.join(errors)
                if ok:
                    # we're OK to add to an event
                    if act_geo is None:
                        act_geo = Geospace()
                    act_geo.uuid = self.manifest.uuid
                    act_geo.project_uuid = self.manifest.project_uuid
                    act_geo.source_id = source_id
                    act_geo.meta_type = post_data['meta_type'].strip()
                    act_geo.ftype = ftype
                    act_geo.feature_id = feature_id
                    act_geo.latitude = latitude
                    act_geo.longitude = longitude
                    act_geo.coordinates = coordinates
                    act_geo.specificity = specificity
                    act_geo.save()
                    note = 'Updated geodata for ' + self.manifest.uuid
        if ok:
            # now clear the cache a change was made
            cache.clear()
        else:
            self.errors = errors
        self.response = {'action': 'add-update-geo-data',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def add_update_project_geo(self, post_data):
        """ Updates a project geospatial data and metadata """
        ok = True
        do_cluster = False
        errors = []
        note = ''
        required_params = ['do_cluster',
                           'proj_geo_specificity',
                           'proj_geo_note']
        for r_param in required_params:
            if r_param not in post_data:
                # we're missing some required data
                # don't create the item
                ok = False
                message = 'Missing paramater: ' + r_param + ''
                errors.append(message)
                note = '; '.join(errors)
        try:
            proj_obj = Project.objects.get(uuid=self.uuid)
        except Project.DoesNotExist:
            message = 'Missing project database object / record for uuid: ' + str(self.uuid)
            errors.append(message)
            ok = False
        if ok:
            proj_geo_specificity = None
            output = self.validate_int_param('proj_geo_specificity', post_data, errors)
            proj_geo_specificity = output['integer']
            errors = output['errors']
            if isinstance(proj_geo_specificity, int):
                if proj_geo_specificity < -20 or proj_geo_specificity > 20:
                    proj_geo_specificity = None
                    message = 'Geo specificity must range between -20 and 20'
                    errors.append(message)
                    ok = False
            proj_geo_note = post_data['proj_geo_note']
            if post_data['do_cluster'] == 'yes':
                # request to make geospatial regions based on clustering locations?
                do_cluster = True
        if ok:
            if do_cluster:
                # delete older geospace records
                Geospace.objects.filter(uuid=self.uuid, item_type='projects').delete()
                pr = ProjectRels()
                pm = ProjectMeta()
                if isinstance(proj_geo_specificity, int):
                    pm.project_specificity = proj_geo_specificity
                elif isinstance(proj_obj.meta_json, dict):
                    if Project.META_KEY_GEO_SPECIFICITY in proj_obj.meta_json:
                        # the project has some default geographic specificity noted
                        # use this value when making geo_meta
                        pm.project_specificity = proj_obj.meta_json[Project.META_KEY_GEO_SPECIFICITY]
                sub_projects = pr.get_sub_projects(self.uuid)
                pm.print_progress = True
                pm.make_geo_meta(self.uuid, sub_projects)
                for geo_obj in pm.geo_objs:
                    try:
                        geo_obj.save()
                    except:
                        pass
                note += 'Added ' + str(len(pm.geo_objs)) + ' cluster-defined geospatial features as project metadata.'
            if isinstance(proj_geo_specificity, int) or len(proj_geo_note) > 1:
                # we are adding geospatial metatada
                if not isinstance(proj_obj.meta_json, dict):
                    proj_obj.meta_json = LastUpdatedOrderedDict()
                if isinstance(proj_geo_specificity, int):
                    proj_obj.meta_json[Project.META_KEY_GEO_SPECIFICITY] = proj_geo_specificity
                if len(proj_geo_note) > 1:
                    proj_obj.meta_json[Project.META_KEY_GEO_NOTE] = proj_geo_note
                else:
                    if Project.META_KEY_GEO_NOTE in proj_obj.meta_json:
                        # remove the note
                        proj_obj.meta_json.pop(Project.META_KEY_GEO_NOTE)
                proj_obj.save()
        if ok:
            # now clear the cache a change was made
            cache.clear()
        else:
            self.errors = errors
            note = '; '.join(errors)
        self.response = {'action': 'add-update-project-geo',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def add_update_date_range(self, post_data):
        """ Updates a file associated with a media item """
        ok = True
        errors = []
        note = ''
        required_params = ['source_id',
                           'hash_id',
                           'earliest',
                           'start',
                           'stop',
                           'latest',
                           'meta_type',
                           'when_type',
                           'feature_id']
        for r_param in required_params:
            if r_param not in post_data:
                # we're missing some required data
                # don't create the item
                ok = False
                message = 'Missing paramater: ' + r_param + ''
                errors.append(message)
                note = '; '.join(errors)
        if ok:
            hash_id = post_data['hash_id'].strip()
            if len(hash_id) < 1:
                hash_id = False
            source_id = post_data['source_id'].strip()
            # validate the dates
            output = self.validate_int_param('earliest', post_data, errors)
            earliest = output['integer']
            errors = output['errors']
            output = self.validate_int_param('start', post_data, errors)
            start = output['integer']
            errors = output['errors']
            output = self.validate_int_param('stop', post_data, errors)
            stop = output['integer']
            errors = output['errors']
            output = self.validate_int_param('latest', post_data, errors)
            latest = output['integer']
            errors = output['errors']
            output = self.validate_int_param('feature_id', post_data, errors)
            feature_id = output['integer']
            if self.manifest.item_type == 'types':
                # we're adding a date range to a type
                feature_id = 0
            errors = output['errors']
            if (earliest is False or start is False \
               or stop is False or latest is False \
               or feature_id is False) and self.manifest.item_type != 'types':
                # 1 or more of the dates are bad
                ok = False
                note = '; '.join(errors)
            else:
                # the dates are all OK.
                # now sort the dates
                time_list = [earliest, start, stop, latest]
                time_list.sort()
                earliest = time_list[0]
                start = time_list[1]
                stop = time_list[2]
                latest = time_list[3]
                act_event = False
                if hash_id is not False:
                    try:
                        act_event = Event.objects.get(hash_id=hash_id)
                    except Event.DoesNotExist:
                        act_event = False
                        ok = False
                        message = 'Cannot find event for hash_id: ' + str(hash_id)
                        errors.append(message)
                        note = '; '.join(errors)
                    if act_event is not False:
                        # get rid of the old event
                        act_event.delete()
                if ok:
                    # we're OK to add to an event
                    act_event = Event()
                    act_event.uuid = self.manifest.uuid
                    act_event.item_type = self.manifest.item_type
                    act_event.project_uuid = self.manifest.project_uuid
                    act_event.source_id = source_id
                    act_event.meta_type = post_data['meta_type'].strip()
                    act_event.when_type = post_data['when_type'].strip()
                    act_event.feature_id = feature_id
                    act_event.earliest = earliest
                    act_event.start = start
                    act_event.stop = stop
                    act_event.latest = latest
                    act_event.save()
                    note = 'Updated date range event for ' + self.manifest.uuid
        if ok:
            # now clear the cache a change was made
            cache.clear()
        self.response = {'action': 'add-update-date-range',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def delete_date_range(self, post_data):
        """ Updates a file associated with a media item """
        ok = True
        errors = []
        note = ''
        required_params = ['hash_id']
        for r_param in required_params:
            if r_param not in post_data:
                # we're missing some required data
                # don't create the item
                ok = False
                message = 'Missing paramater: ' + r_param + ''
                errors.append(message)
                note = '; '.join(errors)
        if ok:
            hash_id = post_data['hash_id'].strip()
            if len(hash_id) < 1:
                ok = False
                message = 'Blank hash_id'
                errors.append(message)
                note = '; '.join(errors)
            if ok:
                try:
                    act_event = Event.objects.get(hash_id=hash_id)
                except Event.DoesNotExist:
                    act_event = False
                    ok = False
                    message = 'Cannot find event for hash_id: ' + str(hash_id)
                    errors.append(message)
                    note = '; '.join(errors)
                if act_event is not False:
                    # get rid of the old event
                    act_event.delete()
                    note = 'Delete event: ' + hash_id + ' for item: ' + self.manifest.uuid
        if ok:
            # now clear the cache a change was made
            cache.clear()
        self.response = {'action': 'delete-date-range',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def validate_int_param(self, param_key, post_data, errors):
        output = {'integer': False,
                  'errors': errors}
        if param_key in post_data:
            try:
                output['integer'] = int(float(post_data[param_key]))
            except:
                output['integer'] = False
                message = 'Need integer for paramater: ' + param_key
                output['errors'].append(message)
        else:
            message = 'Missing parameter: ' + param_key
            output['errors'].append(message)
        return output

    def validate_float_param(self, param_key, post_data, errors):
        output = {'float': False,
                  'errors': errors}
        if param_key in post_data:
            try:
                output['float'] = float(post_data[param_key])
            except:
                output['float'] = False
                message = 'Need float for paramater: ' + param_key
                output['errors'].append(message)
        else:
            message = 'Missing parameter: ' + param_key
            output['errors'].append(message)
        return output

    def validate_geojson(self, geojson_str, errors):
        """ validates geojson """
        output = {'coordinates': False,
                  'type': False,
                  'errors': errors}
        geo_obj = False
        try:
            geo_obj = json.loads(geojson_str)
        except:
            geo_obj = False
            message = 'Cannot parse GeoJSON as JSON'
            errors.append(message)
            output['errors'] = errors
        if isinstance(geo_obj, dict):
            coodinates_found = False
            if 'geometry' in geo_obj:
                geo_obj = geo_obj['geometry']
            if 'type' in geo_obj:
                output['type'] = geo_obj['type']
            if 'coordinates' in geo_obj:
                coordinates_found = True
                output['coordinates'] = json.dumps(geo_obj['coordinates'],
                                                   indent=4,
                                                   ensure_ascii=False)
            else:
                message = 'Cannot find GeoJSON coordinates'
                errors.append(message)
                output['errors'] = errors
        return output
