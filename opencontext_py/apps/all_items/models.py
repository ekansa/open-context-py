import datetime
import decimal
import hashlib
import json
import reversion  # version control object
import uuid as GenUUID

from django.conf import settings

# For geospace manipulations.
from shapely.geometry import mapping, shape

from unidecode import unidecode


from django.db import models

from django.db.models import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items import models_utils

from opencontext_py.libs.validategeojson import ValidateGeoJson
from opencontext_py.libs.models import (
    make_model_object_json_safe_dict,
    json_friendly_datatype_input_obj
)


# A meta_json key to use with AllManifest and AllResource models
# to indicate a URL only supports the http, not https protocol.
META_JSON_KEY_HTTP_ONLY = 'http_only'


# Manifest provides basic item metadata for all open context items that get a URI
@reversion.register  # records in this model under version control
class AllManifest(models.Model):

    OK_FOR_MISSING_REFS = [
        configs.OPEN_CONTEXT_PROJ_UUID,
        configs.OPEN_CONTEXT_PUB_UUID,
        configs.OC_GEN_VOCAB_UUID,
        configs.DEFAULT_CLASS_UUID,
    ]

    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        'self',
        db_column='publisher_uuid',
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        default=configs.OPEN_CONTEXT_PUB_UUID,
    )
    project = models.ForeignKey(
        'self',
        db_column='project_uuid',
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    item_class = models.ForeignKey(
        'self',
        db_column='item_class_uuid',
        related_name='+',
        on_delete=models.CASCADE,
        null=True,
        default=configs.DEFAULT_CLASS_UUID,
    )
    source_id = models.TextField(db_index=True)
    item_type = models.TextField(db_index=True)
    data_type = models.TextField(default='id')
    slug = models.SlugField(max_length=200, unique=True)
    label = models.TextField()
    sort = models.SlugField(max_length=200, db_index=True)
    views = models.IntegerField(default=0)
    indexed = models.DateTimeField(blank=True, null=True)
    vcontrol = models.DateTimeField(blank=True, null=True)
    archived = models.DateTimeField(blank=True, null=True)
    published = models.DateTimeField(db_index=True, null=True)
    revised = models.DateTimeField(db_index=True, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # Note the URI will strip the https:// or http://.
    uri = models.TextField(unique=True)
    # Preferred key when used in JSON-LD.
    item_key = models.TextField(blank=True, null=True)
    # Hash ID has special logic to ensure context dependent uniqueness
    # especially based on the contents of the context field.
    hash_id = models.TextField(unique=True)
    # Context is needed in entity reconciliation, to help determine if
    # a labeled entity is unique within the scope of a given context.
    # Also for URI identified linked-data entities (typically published
    # by sources outside of Open Context, a context is used to note
    # the vocabulary (name-space) that owns / contains a URI identified
    # entity.
    context = models.ForeignKey(
        'self',
        db_column='context_uuid',
        related_name='+',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    # A path is a string / text representation of an entity in a context
    # defined hierarchy. It is used especially for lookups and entity
    # reconciliation of subjects item_types.
    path = models.TextField(db_index=True, blank=True, null=True)
    # Meta_json is where we store occasionally used attributes, such
    # as metadata about projects, persons, languages, etc.
    meta_json = JSONField(default=dict)

    META_JSON_KEY_ATTRIBUTE_GROUP_SLUGS = 'attribute_group_slugs'
    META_JSON_KEY_HTTP_ONLY = META_JSON_KEY_HTTP_ONLY

    def make_table_csv_url(self, url_key='full_csv_url', version=1, filename_suffix='full'):
        """Makes a table item csv download url"""
        if self.item_type != 'tables':
            return None
        csv_url = self.meta_json.get(
            url_key,
            f'{settings.CLOUD_BASE_URL}/{settings.CLOUD_CONTAINER_EXPORTS}/{str(self.uuid)}--v{version}--{filename_suffix}.csv'
        )
        if not csv_url.startswith('http'):
            csv_url = 'https://' + csv_url
        return csv_url

    @property
    def table_full_csv_url(self):
        """Make a url for the datatable full download url"""
        return self.make_table_csv_url()

    @property
    def table_preview_csv_url(self):
        """Make a url for the datatable preview download url"""
        return self.make_table_csv_url(
            url_key='preview_csv_url',
            filename_suffix='head100'
        )


    def clean_label(self, label, item_type='subjects'):
        label = label.strip()
        # So as not to screw up use in javascript
        label = label.replace("'", "’")
        if item_type == 'subjects':
            # So as not to screw up depth of contexts.
            label = label.replace('/', '--')
        if len(label) > 195:
            label = label[:192] + '...'
        return label

    def clean_uri(self, uri):
        if not uri:
            return None
        uri = uri.strip()
        # Trim off the http: or https: prefix.
        for prefix in ['http://', 'https://']:
            if not uri.startswith(prefix):
                continue
            uri = uri[len(prefix):]
        # Remove trailing suffixes that have no meaning.
        for suffix in ['.html', '/', '#']:
            if not uri.endswith(suffix):
                continue
            uri = uri[0:-(len(suffix))]
        return uri

    def make_hash_id(
        self,
        item_type,
        data_type,
        label,
        uri=None,
        path='',
        project_id=configs.OPEN_CONTEXT_PROJ_UUID,
        context_id=configs.OPEN_CONTEXT_PROJ_UUID,
    ):
        """
        Creates a hash-id to ensure context dependent uniqueness
        """
        hash_obj = hashlib.sha1()
        if item_type in configs.URI_ITEM_TYPES:
            concat_string = ' '.join(
                [
                    str(project_id),
                    str(context_id),
                    str(item_type),
                    str(data_type),
                    str(label),
                    str(uri),
                ]
            )
        else:
            concat_string = ' '.join(
                [
                    str(project_id),
                    str(context_id),
                    str(item_type),
                    str(data_type),
                    str(label),
                ]
            )
        if item_type in configs.NODE_ITEM_TYPES:
            # So we can add node sorting value in
            # cases where nodes may have the same
            # label within a project.
            concat_string += path

        concat_string = concat_string.strip()
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def make_hash_id_for_self(self):
        """Makes a hash-id to ensure context dependent uniqueness of this obj"""
        project_id = configs.OPEN_CONTEXT_PROJ_UUID
        context_id = configs.OPEN_CONTEXT_PROJ_UUID
        if self.project:
            project_id = self.project.uuid
        if self.context:
            context_id = self.context.uuid
        path = ''
        if self.path:
            path = self.path
        if self.item_type in configs.NODE_ITEM_TYPES:
            # Add the sort key from the meta_json
            # for node item types. This lets us have
            # the same label for nodes that will
            # may need different sort orders.
            path += str(self.meta_json.get('sort', ''))

        return self.make_hash_id(
            item_type=self.item_type,
            data_type=self.data_type,
            label=self.label,
            uri=self.uri,
            path=path,
            project_id=project_id,
            context_id=context_id,
        )

    def validate_project(self):
        """Checks to make sure a project is actually a project"""
        if self.uuid in self.OK_FOR_MISSING_REFS:
            # Skip this validation because we have
            # a special uuid.
            return True
        # For most cases, check that this a project.
        return models_utils.validate_related_project(project_obj=self.project)

    def validate_from_list(self, option, options, raise_on_error=True):
        if option in options:
            # This is a valid option
            return True
        if raise_on_error:
            raise ValueError('{} not valid, must be in {}'.format(option, str(options)))
        # This is not a valid option
        return False

    def dereference_keys(self):
        """Looks up references to keys"""
        if self.uuid not in self.OK_FOR_MISSING_REFS:
            # Skip out. A manifest object for
            # every uuid except those listed above in
            # ok_for_missing_refs needs to have references to
            # manifest objects that actually exist.
            return None

        # This is a special case for the ok_for_missing_refs
        # list above.
        try:
            self.publisher = self.publisher
        except ObjectDoesNotExist:
            self.publisher = None
        try:
            self.project = self.project
        except ObjectDoesNotExist:
            self.project = None
        try:
            self.item_class = self.item_class
        except ObjectDoesNotExist:
            self.item_class= None
        try:
            self.context = self.context
        except ObjectDoesNotExist:
            self.context = None

    def add_default_short_id_for_project(self):
        """Makes a short_id attribute to projects meta_json"""
        if not self.item_type == 'projects':
            return None
        if not self.meta_json:
            self.meta_json = {}
        if not self.meta_json.get('short_id'):
            self.meta_json['short_id'] = models_utils.suggest_project_short_id()

    def make_slug_and_sort(self):
        """Make slug and sorting values"""
        # Make the slug and sorting
        if self.project:
            project_id = self.project.uuid
        else:
            project_id = None

        short_id = None
        if self.item_type == 'projects' and self.meta_json:
            short_id = self.meta_json.get('short_id')

        if not self.slug:
            # Generate the item's slug.
            self.slug = models_utils.make_manifest_slug(
                self.label,
                self.item_type,
                self.uri,
                project_id,
                short_id=short_id,
            )

        # Make the item's sorting.
        sort = models_utils.make_sort_label(
            self.label,
            self.item_type,
            project_id,
            item_type_list=configs.ITEM_TYPES,
            short_id=short_id,
        )
        self.sort = sort[:100]

    def primary_key_create(
        self,
        item_type,
        project_id=None,
        context_id=None,
        uri=None,
    ):
        """Make a primary key, sometimes deterministically depending on the item_type"""

        if (item_type in configs.OC_ITEM_TYPES
            or project_id is None
            or context_id is None):
            # Do not make a deterministic uuid because these are for
            # formal public publication of items where we have an expectation
            # globally unique identifiers.
            return str(GenUUID.uuid4())

        if item_type in configs.NODE_ITEM_TYPES:
            # Because this is generated randomly, node item types won't
            # have predictable uuids. Only the first part of the uuid will
            # be predictable.
            hash_val = str(GenUUID.uuid4())
        else:
            # This will make a predictable uuid.
            hash_val = self.clean_uri(uri)

        # NOTE: Everything in this function below is for deterministically
        # making a uuid based on the uri, the project_id or the context id.
        hash_obj = hashlib.sha1()
        hash_obj.update(hash_val.encode('utf-8'))
        hash_id =  hash_obj.hexdigest()
        # Now convert that hash into a uuid. Note, we're only using
        # the first 32 characters. This should still be enough to have
        # really, really high certainty we won't have hash-collisions on
        # data that should not be considered unique. If we run into a problem
        # we can always override this.
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')

        # Make the first part from the project uuid.
        project_id = str(project_id)
        uuid_prefix = project_id.split('-')[0]

        if item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
            # Make the first part from the context uuid
            context_id = str(context_id)
            # Grab the second part of the context.
            context_parts = context_id.split('-')
            # project-context-uri_parts...
            uuid = '-'.join(
                [
                    uuid_prefix,
                    context_parts[1],
                    new_parts[2],
                    new_parts[3],
                    new_parts[4],
                ]
            )
        else:
            # project-uri_parts...
            uuid = '-'.join(
                ([uuid_prefix] + new_parts[1:])
            )
        return uuid

    def validate_item_type_class_item(self, item_type, item_class_id, raise_on_fail=True):
        """Validates class_item by item_type"""
        class_configs = {
            'predicates': configs.CLASS_LIST_OC_PREDICATES,
            'persons': configs.CLASS_LIST_OC_PERSONS,
            'media': configs.CLASS_LIST_OC_MEDIA,
        }
        if item_type not in class_configs:
            # No configured item_class validation check for this item type.
            return True
        item_class_id = str(item_class_id)
        allowed_class_ids = class_configs.get(item_type)
        if item_class_id in allowed_class_ids:
            # The item_class_id is in the expected allowed item_class ids
            # for this item_type. Validates OK.
            return True
        if not raise_on_fail:
            # We ran into a problem but don't want to raise an exception.
            return False
        raise ValueError(
            f'{item_class_id} is not in allowed {item_type} item_class '
            f'must be: {str(allowed_class_ids)}'
        )

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_type=self.item_type,
            project_id=self.project.uuid,
            context_id=self.context.uuid,
            uri=self.uri,
        )

    def make_subjects_path_and_validate(self):
        """Makes a path for subjects items"""
        if self.item_type != 'subjects':
            return self.path
        if str(self.uuid) in configs.DEFAULT_SUBJECTS_ROOTS:
            # We're at the "root", no path.
            self.path = ''
            return self.path
        if str(self.uuid) in configs.LIST_SUBJECTS_WORLD_REGIONS_UUIDS:
            self.path = self.label
            return self.path
        if str(self.context.uuid) == configs.DEFAULT_SUBJECTS_OFF_WORLD_UUID:
            self.path = self.context.label + '/' + self.label
            return self.path
        if self.context.item_type != 'subjects':
            raise ValueError(
                f'Context must have item_type="subjects" not {self.context.item_type}'
            )
        self.path = self.context.path + '/' + self.label
        self.path = self.path.replace("'", "`")
        return self.path

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        self.label = self.clean_label(self.label, self.item_type)
        self.uri = self.clean_uri(self.uri)

        # Makes sure that subjects items have a path defined, and a
        # context item of the correct type.
        self.make_subjects_path_and_validate()

        # Dereferences keys:
        self.dereference_keys()

        # Depending on the item type, make a random, semi-random,
        # or totally predicable uuid for this manifest obj.
        self.uuid = self.primary_key_create_for_self()

        # Make the URI for Open Context item types.
        if self.item_type in (
            configs.OC_ITEM_TYPES
            + configs.NODE_ITEM_TYPES
        ):
            self.uri = models_utils.make_uri_for_oc_item_types(
                self.uuid,
                self.item_type
            )

        # Add revised if it doesn't exist
        if not self.revised:
            self.revised = timezone.now()

        # Make sure the project is actually a project
        self.validate_project()

        self.hash_id = self.make_hash_id_for_self()
        # Make sure the item_type is valid.
        self.validate_from_list(
            self.item_type, configs.ITEM_TYPES
        )
        # Make sure the data_type is valid.
        self.validate_from_list(
            self.data_type, configs.DATA_TYPES
        )
        # Make sure predicates, persons, and media have an expected class
        if self.source_id != configs.DEFAULT_SOURCE_ID:
            item_class_id = None
            if self.item_class:
                item_class_id = self.item_class.uuid
            # Only do this validation for non-default loads.
            self.validate_item_type_class_item(
                item_type=self.item_type,
                item_class_id=item_class_id
            )
        # Add a project short_id:
        self.add_default_short_id_for_project()
        # Make the slug and sort values.
        self.make_slug_and_sort()
        super(AllManifest, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.uuid}: {self.label}; {self.item_type}'

    class Meta:
        db_table = 'oc_all_manifest'
        default_related_name = 'manifests'


# NOTE: AllSpaceTime keeps geospatial and chronology records.
# Some records have both geospatial and chronology components,
# some only have geospatial, and some only have chronology.
# Each record is linked to an item and an event. An event is
# basically some identified entity in space and/or time that
# involves the item.
@reversion.register  # records in this model under version control
class AllSpaceTime(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        AllManifest,
        db_column='publisher_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.OPEN_CONTEXT_PUB_UUID,
    )
    project = models.ForeignKey(
        AllManifest,
        db_column='project_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    source_id = models.TextField(db_index=True)
    item = models.ForeignKey(
        AllManifest,
        db_column='item_uuid',
        related_name='item_uuid',
        on_delete=models.CASCADE
    )
    event = models.ForeignKey(
        AllManifest,
        db_column='event_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.DEFAULT_EVENT_UUID,
    )
    # An integer ID, used for sorting, that is unique to the
    # specific item.
    feature_id = models.IntegerField(default=1)

    # Time span information.
    earliest = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    start = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    stop = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    latest = models.DecimalField(max_digits=19, decimal_places=5, null=True)

    # Location information.
    geometry_type = models.TextField(null=True)
    latitude = models.DecimalField(max_digits=24, decimal_places=21, null=True)
    longitude = models.DecimalField(max_digits=24, decimal_places=21, null=True)
    geo_specificity = models.IntegerField(default=0, null=True)
    # The geometry is a GeoJSON geometry object.
    geometry = JSONField(default=dict, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    # Geometry types that we allow.
    GEOMETRY_TYPES = [
        'Point',
        'LineString',
        'Polygon',
        'MultiPoint',
        'MultiLineString',
        'MultiPolygon',
    ]

    def validate_times(
        self,
        earliest=None,
        start=None,
        stop=None,
        latest=None,
    ):
        """
        makes sure time data is properly validated
        """
        raw_time_list = [earliest, start, stop, latest]
        time_list = []
        for raw_time in raw_time_list:
            if isinstance(raw_time, str):
                try:
                    raw_time = float(raw_time)
                except:
                    raw_time = None
            if raw_time is None:
                continue
            time_list.append(raw_time)

        time_list = list(set(time_list))
        if not len(time_list):
            return (
                None,
                None,
                None,
                None,
            )

        # Sort the list, then fill in any blanks.
        time_list.sort()
        while len(time_list) < 4:
            time_list.append(max(time_list))

        if time_list[1] == max(time_list):
            time_list[1] = min(time_list)
        if time_list[2] == min(time_list):
            time_list[2] = max(time_list)

        return (
            min(time_list),
            time_list[1],
            time_list[2],
            max(time_list),
        )

    def validate_times_for_self(self):
        """
        makes sure time data is properly validated
        """
        self.earliest, self.start, self.stop, self.latest = self.validate_times(
            self.earliest,
            self.start,
            self.stop,
            self.latest,
        )

    def make_hash_id(
        self,
        item_id,
        event_id=configs.DEFAULT_EVENT_UUID,
        earliest=None,
        start=None,
        stop=None,
        latest=None,
        latitude=None,
        longitude=None,
        geometry=None,
    ):
        """Makes a hash_id for an assertion"""
        earliest, start, stop, latest = self.validate_times(
            earliest,
            start,
            stop,
            latest,
        )
        hash_obj = hashlib.sha1()
        concat_list = [
            str(item_id),
            str(event_id),
            str(earliest),
            str(start),
            str(stop),
            str(latest),
            str(latitude),
            str(longitude),
        ]
        if isinstance(geometry, dict):
            concat_list += [
                str(geometry.get('type')),
                str(geometry.get('coordinates')),
            ]
        concat_string = " ".join(concat_list)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def primary_key_create(
        self,
        item_id,
        event_id=configs.DEFAULT_EVENT_UUID,
        earliest=None,
        start=None,
        stop=None,
        latest=None,
        latitude=None,
        longitude=None,
        geometry=None,
    ):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]

        hash_id = self.make_hash_id(
            item_id=item_id,
            event_id=event_id,
            earliest=earliest,
            start=start,
            stop=stop,
            latest=latest,
            latitude=latitude,
            longitude=longitude,
            geometry=geometry,
        )
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid,
            event_id=self.event.uuid,
            earliest=self.earliest,
            start=self.start,
            stop=self.stop,
            latest=self.latest,
            latitude=self.latitude,
            longitude=self.longitude,
            geometry=self.geometry,
        )

    def determine_feature_id(self, item_id, exclude_uuid=None):
        """Makes a feature if missing"""
        f_id_qs = AllSpaceTime.objects.filter(
            item_id=item_id,
        )
        if exclude_uuid:
            # exclude a UUID from the query list.
            f_id_qs = f_id_qs.exclude(uuid=exclude_uuid)

        # Now make a value_list for the feature id.
        f_id_qs = f_id_qs.order_by(
            'feature_id'
        ).distinct(
            'feature_id'
        ).values_list('feature_id', flat=True)
        f_ids = [id for id in f_id_qs]
        if not len(f_ids):
            return 1
        return max(f_ids) + 1

    def determine_feature_id_for_self(self):
        """Makes a feature if missing"""
        if self.feature_id is not None:
            return self.feature_id
        return self.determine_feature_id(
            item_id=self.item.uuid,
            exclude_uuid=self.uuid,
        )

    def validate_longitude(self, lon):
        if not isinstance(lon, float) and not isinstance(lon, decimal.Decimal):
            return False
        return (-180 <= lon <= 180)

    def validate_latitude(self, lat):
        if not isinstance(lat, float) and not isinstance(lat, decimal.Decimal):
            return False
        return (-90 <= lat <= 90)

    def validate_correct_geometry(self):
        """Validates and corrects the geometry object"""
        if not self.geometry_type:
            # None of these other validations apply, because
            # we do not have a geometry type specified.
            return None
        elif self.geometry_type == 'Point':
            # Make the geometry object based on the lat, lon.
            self.geometry = {
                'type': self.geometry_type,
                'coordinates':  [
                    float(self.longitude),
                    float(self.latitude),
                ],
            }
        else:
            # Not a point, so do some more complex validation.
            if self.geometry.get('type') != self.geometry_type:
                raise ValueError(
                    f'Geometry dict type { self.geometry.get("type") } must '
                    f'agree with geometry_type {self.geometry_type}'
                )
            if not self.geometry.get('coordinates'):
                raise ValueError(
                    f'Geometry dict type { self.geometry.get("type") } must '
                    'have coordinates'
                )
            # Make the coordinates have the correct GeoJSON ordering.
            v_geojson = ValidateGeoJson()
            self.geometry['coordinates'] = v_geojson.fix_geometry_rings_dir(
                self.geometry_type,
                self.geometry['coordinates']
            )
            if not isinstance(self.geometry.get('coordinates'), list):
                raise ValueError(
                    f'Geometry dict type { self.geometry.get("type") } must '
                    'have a list of coordinates'
                )

        if self.geometry_type not in self.GEOMETRY_TYPES:
            raise ValueError(
                f'Geometry type { self.geometry_type } must '
                f'be of {str(self.GEOMETRY_TYPES)}'
            )

        if self.longitude is None or self.latitude is None:
            # We don't have the centroid, so calculate it from the
            # geometry object.
            s = shape(self.geometry)
            coords = s.centroid.coords[0]
            self.longitude = coords[0]
            self.latitude = coords[1]

        # Now validate that we actually have a latitude and longitude coordinate
        # pair.
        if self.longitude is None or self.latitude is None:
            raise ValueError(
                f'Geometry {self.geometry_type} must '
                'have latitude and longitude coordinates.'
            )

        if isinstance(self.longitude, str):
            try:
                self.longitude = float(self.longitude)
            except:
                raise ValueError(
                    f'Coordinate {self.longitude} must '
                    'be numeric.'
                )
        if isinstance(self.latitude, str):
            try:
                self.latitude = float(self.latitude)
            except:
                raise ValueError(
                    f'Coordinate {self.longitude} must '
                    'be numeric.'
                )

        if not self.validate_longitude(self.longitude):
            raise ValueError(
                f'Longitude must be between -180 and 180'
            )

        if not self.validate_latitude(self.latitude):
            raise ValueError(
                f'Latitude must be between -90 and 90'
            )

    def save(self, *args, **kwargs):
        """
        Saves with validation checks.
        """
        self.earliest, self.start, self.stop, self.latest = self.validate_times(
            self.earliest,
            self.start,
            self.stop,
            self.latest,
        )
        # Make sure the project is really a project.
        models_utils.validate_related_project(project_obj=self.project)
        # Projects, subjects, and types (for periods) can have time space information.
        models_utils.validate_related_manifest_item_type(
            man_obj=self.item,
            allowed_types= [
                'projects',
                'subjects',
                'documents',
                'media',
                'types',
                'predicates',
                'tables',
                'uri',
                'class',
            ],
            obj_role='item',
        )

        # Validate the event.
        models_utils.validate_related_manifest_item_type(
            man_obj=self.event,
            allowed_types=['events'],
            obj_role='event',
        )

        # Validates the geometry dict, make sure the coordinates are in the
        # correct GeoJSON order.
        self.validate_correct_geometry()

        self.primary_key_create_for_self()
        self.feature_id = self.determine_feature_id_for_self()
        super(AllSpaceTime, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_spacetime'
        unique_together = (
            (
                "item",
                "event",
            ),
            (
                "item",
                "feature_id",
            ),
        )
        ordering = ["item", "feature_id",]
        default_related_name = 'spacetimes'





# AllAssertion stores data about "assertions" made about and using items in the AllManifest
# model. It's a very schema-free / graph like model for representing relationships and
# attributes of items from different sources. But it is not a triple store because we
# have several metadata attributes (publisher, project, observation, event,
# attribute_group, etc.) that provide additional context to make things hopefully
# easier to manage.
@reversion.register  # records in this model under version control
class AllAssertion(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        AllManifest,
        db_column='publisher_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.OPEN_CONTEXT_PUB_UUID,
    )
    project = models.ForeignKey(
        AllManifest,
        db_column='project_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    source_id = models.TextField(db_index=True)
    subject = models.ForeignKey(
        AllManifest,
        db_column='subject_uuid',
        related_name='subject_uuid',
        on_delete=models.CASCADE
    )
    # Observations are nodes for grouping related assertions, perhaps
    # made by different people.
    observation = models.ForeignKey(
        AllManifest,
        db_column='observation_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.DEFAULT_OBS_UUID,
    )
    obs_sort = models.IntegerField(default=1)
    # Events are nodes for identifying specific space-time grouped
    # assertions.
    event = models.ForeignKey(
        AllManifest,
        db_column='event_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.DEFAULT_EVENT_UUID,
    )
    event_sort = models.IntegerField(default=1)
    # Attribute groups are for modeling predicate and object values
    # that need to be understood as a group. For example, a ratio
    # with a numerator and a denominator are 3 grouped assertions that
    # would make sense together in an attribute group.
    attribute_group = models.ForeignKey(
        AllManifest,
        db_column='attribute_group_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    )
    attribute_group_sort = models.IntegerField(default=1)
    predicate = models.ForeignKey(
        AllManifest,
        db_column='predicate_uuid',
        related_name='+',
        on_delete=models.CASCADE
    )
    sort = models.FloatField(null=True, default=1)
    # Th attribute 'visible' can be set to False to indicate that an assertion is no longer
    # current. If so, it can be used to maintain a record of changes, especially
    # with metadata about changes stored in meta_json.
    visible = models.BooleanField(default=True)
    # Estimated probability for an assertion
    # (with 1 as 100% certain, .001 for very uncertain), null for not determined.
    certainty = models.FloatField(null=True)
    object = models.ForeignKey(
        AllManifest,
        db_column='object_uuid',
        related_name='+',
        on_delete=models.CASCADE,
        default=configs.DEFAULT_NULL_OBJECT_UUID,
    )
    language =  models.ForeignKey(
        AllManifest,
        db_column='language_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        default=configs.DEFAULT_LANG_UUID
    )
    # This obj_string_hash is a hash of the obj_string field used to help in unique
    # constraints for assertions.
    obj_string_hash = models.TextField()
    # The following fields are for object literals.
    obj_string = models.TextField(null=True)
    obj_boolean = models.BooleanField(null=True)
    obj_integer = models.BigIntegerField(null=True)
    obj_double = models.DecimalField(max_digits=19, decimal_places=10, null=True)
    obj_datetime = models.DateTimeField(null=True)
    # The following fields are some administrative metadata about assertions.
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def validate_node_refs(self):
        """Validates references to 'node' manifest objects"""
        checks = [
            (self.observation, ['observations'], 'observation',),
            (self.event, ['events'], 'event',),
            (self.attribute_group, ['attribute-groups'], 'attribute_group',),
            (self.language, ['languages'], 'language',),
        ]
        for relate_obj, allowed_types, obj_role in checks:
            models_utils.validate_related_manifest_item_type(
                man_obj=relate_obj,
                allowed_types=allowed_types,
                obj_role=obj_role
            )

    def validate_predicate(self):
        """Validates predicate is an OK type to be a predicate"""
        # NOTE: For the purposes of this validation, a
        # an item_type='class' item can act as a predicate (attribute) to make
        # it easier to represent measurements, which are defined as classes
        # in the CIDOC-CRM (see: http://erlangen-crm.org/current/E54_Dimension )
        # In this case, an assertion using a predicate object that is a
        # measurement class would be read something like:
        #
        # subject -> has_measurement::dimension::has-value -> 1.1
        #
        # where the has_measurement::dimension::has-value is all implied by
        # within the predicate object of this assertion.
        models_utils.validate_related_manifest_item_type(
            man_obj=self.predicate,
            allowed_types= ['predicates', 'property', 'class'],
            obj_role='predicate',
        )

    def validate_predicate_objects(self):
        """Validates that predicates have objects of the correct type"""
        object_expectations = [
            (
                (self.object.uuid == GenUUID.UUID(str(configs.DEFAULT_NULL_OBJECT_UUID))),
                (self.predicate.data_type == 'id'),
            ),
            (
                (self.obj_string is None),
                (self.predicate.data_type == 'xsd:string'),
            ),
            (
                (self.obj_boolean is None),
                (self.predicate.data_type == 'xsd:boolean'),
            ),
            (
                (self.obj_integer is None),
                (self.predicate.data_type == 'xsd:integer'),
            ),
            (
                (self.obj_double is None),
                (self.predicate.data_type == 'xsd:double'),
            ),
            (
                (self.obj_datetime is None),
                (self.predicate.data_type == 'xsd:date'),
            ),
        ]
        for data_type_is_none, should_exist in object_expectations:
            if should_exist:
                assert not data_type_is_none
            else:
                assert data_type_is_none

    def validate_predicate_class_objects(self):
        """Validates that predicates of item_type predicates have
           objects of the appropriate class"""
        if self.predicate.item_type != 'predicates':
            # This check does not apply.
            return None
        if self.predicate.data_type != 'id':
            # Object is not a named entity, so this check does not
            # apply
            return None
        if str(self.predicate.item_class.uuid) == str(configs.CLASS_OC_VARIABLES_UUID):
            if self.object.item_type != 'types':
                raise(
                    f'Object of predicate {self.predicate.label}, '
                    f'a {self.predicate.item_class.label} ({str(self.predicate.item_class.uuid)})'
                    f'must be item_type = "types"'
                )
        if str(self.predicate.item_class.uuid) == str(configs.CLASS_OC_LINKS_UUID):
            if not self.object.item_type in configs.OC_PRED_LINK_OK_ITEM_TYPES:
                raise(
                    f'Object of predicate {self.predicate.label}, '
                    f'a {self.predicate.item_class.label} ({str(self.predicate.item_class.uuid)})'
                    f'must be item_type in {str(configs.OC_PRED_LINK_OK_ITEM_TYPES)}'
                )

    def make_obj_string_hash(self, obj_string):
        """Makes an object string hash value"""
        if obj_string:
            obj_string = obj_string.strip()
            hash_obj = hashlib.sha1()
            hash_obj.update(str(obj_string).encode('utf-8'))
            return hash_obj.hexdigest()
        else:
            # No string value to hash, so return something
            # small to be nice to our index.
            return '0'

    def make_hash_id(
        self,
        subject_id,
        predicate_id,
        object_id=None,
        obj_string=None,
        obj_boolean=None,
        obj_integer=None,
        obj_double=None,
        obj_datetime=None,
        observation_id=configs.DEFAULT_OBS_UUID,
        event_id=configs.DEFAULT_EVENT_UUID,
        attribute_group_id=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
        language_id=configs.DEFAULT_LANG_UUID,
    ):
        """Makes a hash_id for an assertion"""
        if obj_string:
            obj_string = obj_string.strip()

        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(subject_id),
                str(observation_id),
                str(event_id),
                str(attribute_group_id),
                str(predicate_id),
                str(object_id),
                str(language_id),
                str(obj_string),
                str(obj_boolean),
                str(obj_integer),
                str(obj_double),
                str(obj_datetime),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def primary_key_create(
        self,
        subject_id,
        predicate_id,
        object_id=None,
        obj_string=None,
        obj_boolean=None,
        obj_integer=None,
        obj_double=None,
        obj_datetime=None,
        observation_id=configs.DEFAULT_OBS_UUID,
        event_id=configs.DEFAULT_EVENT_UUID,
        attribute_group_id=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
        language_id=configs.DEFAULT_LANG_UUID,
    ):
        """Deterministically make a primary key using a prefix from the subject"""

        # Make the first part from the subject's uuid.
        subject_id = str(subject_id)
        uuid_prefix = subject_id.split('-')[0]

        # Make a hash for this Assertion based on all those parts
        # that need to be unique.
        hash_id = self.make_hash_id(
            subject_id=subject_id,
            predicate_id=predicate_id,
            object_id=object_id,
            obj_string=obj_string,
            obj_boolean=obj_boolean,
            obj_integer=obj_integer,
            obj_double=obj_double,
            obj_datetime=obj_datetime,
            observation_id=observation_id,
            event_id=event_id,
            attribute_group_id=attribute_group_id,
            language_id=language_id,
        )
        # Now convert that hash into a uuid. Note, we're only using
        # the first 32 characters. This should still be enough to have
        # really, really high certainty we won't have hash-collisions on
        # data that should not be considered unique. If we run into a problem
        # we can always override this.
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([uuid_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid

        object_id = None
        if self.object is not None:
            object_id = self.object.uuid

        self.uuid = self.primary_key_create(
            subject_id=self.subject.uuid,
            predicate_id=self.predicate.uuid,
            object_id=object_id,
            obj_string=self.obj_string,
            obj_boolean=self.obj_boolean,
            obj_integer=self.obj_integer,
            obj_double=self.obj_double,
            obj_datetime=self.obj_datetime,
            observation_id=self.observation.uuid,
            event_id=self.event.uuid,
            attribute_group_id=self.attribute_group.uuid,
            language_id=self.language.uuid,
        )
        return self.uuid

    def get_display_object(self, add_id=True):
        """Gets the display object for an assertion"""
        if add_id and self.predicate.data_type == 'id':
            return f'{self.object.label} [{self.object.uuid}]'
        elif not add_id and self.predicate.data_type == 'id':
            return f'{self.object.label}'
        elif self.predicate.data_type == 'xsd:string':
           return f'"{self.obj_string[:20]}"'
        elif self.predicate.data_type == 'xsd:boolean':
            return f'{self.obj_boolean}'
        elif self.predicate.data_type == 'xsd:integer':
            return f'{self.obj_integer}'
        elif self.predicate.data_type == 'xsd:double':
            return f'{self.obj_double}'
        elif self.predicate.data_type == 'xsd:date':
            return f'{self.obj_datetime}'
        return ''

    def save(self, *args, **kwargs):
        """
        Creates the hash-id on saving to insure a unique string for a project
        """
        # Make sure the project is really a project.
        models_utils.validate_related_project(project_obj=self.project)
        # Make sure that nodes in this assertion have the expected item_types.
        self.validate_node_refs()
        # Make sure the predicate is a predicate or property item_type
        self.validate_predicate()

        if self.obj_string:
            self.obj_string = self.obj_string.strip()

        # This is set with each save to help make sure the text field is actually
        # unique. It's important for long text values.
        self.obj_string_hash = self.make_obj_string_hash(self.obj_string)

        self.uuid = self.primary_key_create_for_self()

        # Make sure that the data_type expected of the predicate is enforced.
        self.validate_predicate_objects()
        # Make sure hierarchy assertions are valid, not circular
        models_utils.validate_hierarchy_assertion(
            subject_obj=self.subject,
            predicate_obj=self.predicate,
            object_obj=self.object,
        )
        # Make sure assertions about units of measure are valid.
        models_utils.validate_has_unit_assertion(
            predicate_obj=self.predicate,
            object_obj=self.object
        )
        if not self.obs_sort:
            self.obs_sort = self.observation.meta_json.get(
                'sort', 1
            )
        if not self.event_sort:
            self.event_sort = self.event.meta_json.get(
                'sort', 1
            )
        if not self.attribute_group_sort:
            self.attribute_group_sort = self.attribute_group.meta_json.get(
                'sort', 1
            )
        if not self.sort:
            self.sort = self.predicate.meta_json.get(
                'sort', 1
            )

        super(AllAssertion, self).save(*args, **kwargs)

    def __str__(self):
        out = (
            f'{self.uuid}: {self.subject.label} [{self.subject.uuid}] '
            f'-> {self.predicate.label} [{self.predicate.uuid}] -> '
        )
        out += self.get_display_object()
        return out

    class Meta:
        db_table = 'oc_all_assertions'
        unique_together = (
            (
                "subject",
                "observation",
                "event",
                "attribute_group",
                "predicate",
                "object",
                "language",
                "obj_string_hash",
                "obj_boolean",
                "obj_integer",
                "obj_double",
                "obj_datetime"
            ),
        )
        ordering = ["subject", "obs_sort", "event_sort", "attribute_group_sort", "sort"]
        default_related_name = 'assertions'
        # Custom additional indexes to make search faster
        indexes = [
            models.Index(fields=["subject", "visible"], name="subject_visible_idx"),
            models.Index(fields=["subject", "predicate", "visible"], name="subject_predicate_visible_idx"),
            models.Index(fields=["subject", "object", "visible"], name="subject_object_visible_idx"),
            models.Index(fields=["predicate", "visible"], name="predicate_visible_idx"),
            models.Index(fields=["object", "visible"], name="object_visible_idx"),
        ]



# Records files (usually media files, like images, but )
@reversion.register  # records in this model under version control
class AllResource(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    item = models.ForeignKey(
        AllManifest,
        db_column='item_uuid',
        related_name='+',
        on_delete=models.PROTECT
    )
    project = models.ForeignKey(
        AllManifest,
        db_column='project_uuid',
        related_name='+',
        on_delete=models.PROTECT,
    )
    resourcetype = models.ForeignKey(
        AllManifest,
        db_column='resourcetype_uuid',
        related_name='+',
        on_delete=models.PROTECT,
    )
    mediatype = models.ForeignKey(
        AllManifest,
        db_column='mediatype_uuid',
        related_name='+',
        on_delete=models.PROTECT,
        null=True
    )
    source_id = models.TextField(db_index=True)
    uri = models.TextField()
    sha256_checksum = models.TextField(null=True)
    filesize = models.DecimalField(max_digits=19, decimal_places=3, null=True)
    rank = models.IntegerField(default=0)
    is_static = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    META_JSON_KEY_HTTP_ONLY = META_JSON_KEY_HTTP_ONLY

    def make_hash_id(
        self,
        item_id,
        resourcetype_id,
        rank=0,
    ):
        """Makes a hash_id for an assertion"""
        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(item_id),
                str(resourcetype_id),
                str(rank),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def primary_key_create(self, item_id, resourcetype_id, rank=0):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]

        hash_id = self.make_hash_id(
            item_id=item_id,
            resourcetype_id=resourcetype_id,
            rank=rank,
        )
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid,
            resourcetype_id=self.resourcetype.uuid,
            rank=self.rank
        )

    def save(self, *args, **kwargs):
        """
        Makes the primary key sorted for the first part
        of the item uuid
        """
        self.uuid = self.primary_key_create_for_self()
        self.uri = AllManifest().clean_uri(self.uri)
        # Make sure the project is really a project.
        models_utils.validate_related_project(
            project_obj=self.project
        )
        # Make sure the associated item has the right types
        models_utils.validate_related_manifest_item_type(
            man_obj=self.item,
            allowed_types=['projects', 'tables', 'media', 'uri',],
            obj_role='item'
        )
        # Make sure the resource type is in a pre-configured
        # list of valid resource types.
        models_utils.validate_resourcetype_id(
            resourcetype_id=self.resourcetype.uuid
        )

        # Make an HTTP head request to get filesize and/or
        # mediatype if missing.
        head = None
        if not self.filesize or self.mediatype is None:
            head = models_utils.get_web_resource_head_info(
                self.uri
            )
        if head and not self.filesize:
            self.filesize = head.get('filesize')
        if head and not self.mediatype:
            self.mediatype = head.get('mediatype')

        # If given, make sure the item mimetype
        # has the correct manifest item_type.
        if self.mediatype:
            models_utils.validate_related_manifest_item_type(
                man_obj=self.mediatype,
                allowed_types=['media-types'],
                obj_role='mediatype'
            )

        super(AllResource, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_resources'
        unique_together = (
            (
                "item",
                "resourcetype",
                "rank",
            ),
        )
        ordering = ["item", "rank", "resourcetype",]
        default_related_name = 'resources'


# Records a hash history of an item for use in version control.
@reversion.register  # records in this model under version control
class AllHistory(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    sha1_hash = models.TextField(unique=True)
    item = models.ForeignKey(
        AllManifest,
        db_column='item_uuid',
        related_name='+',
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)


    def get_model_objs_for_history(self, item_id):
        """Gets model objects relating to an item_id for making a history"""
        man_qs = AllManifest.objects.filter(uuid=item_id)[:1]
        if not len( man_qs):
            return None

        all_model_objs = {
            AllManifest._meta.label: man_qs,
        }
        other_models = [
            AllSpaceTime,
            AllAssertion,
            AllResource,
            AllIdentifier,
        ]
        for act_model in other_models:
            if act_model._meta.label == 'all_items.AllAssertion':
                # The main item is the subject of the assertions.
                qs =  act_model.objects.filter(subject=man_qs[0])
            else:
                qs = act_model.objects.filter(item=man_qs[0])
            all_model_objs[act_model._meta.label] = qs
        return all_model_objs

    def get_model_dicts_for_history(self, item_id):
        """Gets model objects relating to an item_id for making a history"""
        all_model_objs = self.get_model_objs_for_history(item_id)
        if not all_model_objs:
            return None
        all_model_dicts = {}
        for model_key, qs in all_model_objs.items():
            all_model_dicts[model_key] = []
            for model_obj in qs:
                model_dict = make_model_object_json_safe_dict(model_obj)
                all_model_dicts[model_key].append(model_dict)
        return all_model_dicts

    def calculate_sha1_hash_from_all_model_dicts(self, all_model_dicts):
        """Calculates a sha1 hash from all_model_dicts"""
        if not all_model_dicts:
            return None
        clean_model_dicts = []
        i = 0
        now = datetime.datetime.now()
        clean_model_dicts = [now.isoformat()]
        for model_dict in all_model_dicts:
            if isinstance(model_dict, dict):
                for key, val in model_dict.items():
                    model_dict[key] = json_friendly_datatype_input_obj(val)
            clean_model_dicts.append(model_dict)
            clean_model_dicts.append(i)
            i += 1
        item_json = json.dumps(clean_model_dicts, ensure_ascii=False)
        encoded_str = item_json.encode()
        # create a sha1 hash object initialized with the encoded string
        hash_obj = hashlib.sha1(encoded_str)
        return hash_obj.hexdigest()

    def calculate_sha1_hash_for_item(self, item_id, use_time=False):
        """Makes a sha1 hash for an item"""
        all_model_dicts = self.get_model_dicts_for_history(item_id)
        if not all_model_dicts:
            return None
        if use_time:
            all_model_dicts['updated'] = timezone.now().isoformat()
        return self.calculate_sha1_hash_from_all_model_dicts(all_model_dicts)

    def calculate_sha1_hash_for_self(self, use_time=False):
        """Make sha1 hash for self"""
        if not self.item:
            return None
        return self.calculate_sha1_hash_for_item(self.item.uuid, use_time=use_time)

    def primary_key_create(self, item_id, sha1_hash):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]

        uuid_from_hash_id = str(
            GenUUID.UUID(hex=sha1_hash[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid,
            sha1_hash=self.sha1_hash,
        )

    def save(self, *args, **kwargs):
        """
        Makes the primary key sorted for the first part
        of the subject uuid
        """
        if not self.sha1_hash:
            self.sha1_hash = self.calculate_sha1_hash_for_self()

        self.uuid = self.primary_key_create_for_self()
        if False:
            # Make sure the item has the right
            # manifest object item_type (open context items)
            models_utils.validate_related_manifest_item_type(
                man_obj=self.item,
                allowed_types=configs.OC_ITEM_TYPES,
                obj_role='item'
            )
        super(AllHistory, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_history'
        ordering = ["item", "updated",]
        default_related_name = 'histories'



# Records identifiers associated with oc_items.
@reversion.register  # records in this model under version control
class AllIdentifier(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    item = models.ForeignKey(
        AllManifest,
        db_column='item_uuid',
        related_name='+',
        on_delete=models.CASCADE
    )
    scheme = models.TextField()
    rank = models.IntegerField(default=0)
    id =  models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    SCHEME_CONFIGS = {
        'doi': {
            'url_root': 'doi.org/',
            'limit_item_types': None
        },
        'ark': {
            'url_root': 'n2t.net/ark:/',
            'limit_item_types': None
        },
        'orcid': {
            'url_root': 'orcid.org/',
            'limit_item_types':
            ['persons'],
        },
    }


    def make_id_url(self, scheme, id, protocol_prefix=''):
        """Makes a URL from a scheme and id"""
        # NOTE: this can be invoked without a
        # model object
        conf = self.SCHEME_CONFIGS.get(scheme, {})
        url_root = conf.get('url_root')
        if not url_root:
            return None
        return f'{protocol_prefix}{url_root}{id}'


    @property
    def url(self):
        """Make a url based on the scheme and id"""
        return self.make_id_url(self.scheme, self.id)

    def make_hash_id(self, item_id, scheme, rank=0):
        """Makes a hash_id for an assertion"""
        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(item_id),
                str(scheme),
                str(rank),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def primary_key_create(self, item_id, scheme, rank=0):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]

        hash_id = self.make_hash_id(
            item_id=item_id,
            scheme=scheme,
            rank=rank,
        )
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid,
            scheme=self.scheme,
            rank=self.rank
        )


    def normalize_validate_id_in_scheme(self, id, scheme=None):
        """Normalizes and validates an identifier"""
        id = id.strip()
        for scheme_key, config in self.SCHEME_CONFIGS.items():
            url_root = config.get('url_root')
            if not url_root:
                continue
            if not url_root in id:
                continue
            # Everything below happens if the id has the URL root
            # in it. This means we can check it its a DOI, ARK or ORCID
            # and it means we should remove the url_root from the ID
            # so as to keep nicely consistent data where we don't have
            # the url_roots saved.
            if id.startswith('http://') or id.startswith('https://'):
                # We're getting a Web URI as an identifier
                id = AllManifest().clean_uri(id)
            if not scheme:
                scheme = scheme_key
            elif scheme and scheme != scheme_key:
                raise ValueError(
                    f'ID {id} not valid for scheme {scheme}. '
                    f'It should be {scheme_key} because it contains {url_root}'
                )
            id_ex = id.split(url_root)
            if len(id_ex) <= 1:
                raise ValueError(
                    f'ID {id} not valid for scheme {scheme}. String invalid, too small with {url_root}'
                )
            id = id_ex[-1].strip()
        if not scheme:
            raise ValueError(
                f'ID {id} not valid because no scheme indicated'
            )
        if not id:
            raise ValueError(
                f'ID is empty'
            )
        return id, scheme


    def save(self, *args, **kwargs):
        """
        Makes the primary key sorted for the first part
        of the subject uuid
        """

        # Make sure we have identifiers that meet expectations for their scheme
        id, scheme = self.normalize_validate_id_in_scheme(self.id, scheme=self.scheme)
        self.id = id
        self.scheme = scheme

        self.uuid = self.primary_key_create_for_self()
        if self.scheme not in configs.IDENTIFIER_SCHEMES:
            raise ValueError(
                f'ID scheme {self.scheme} not in {str(configs.IDENTIFIER_SCHEMES)}'
            )
        # Make sure the item has the right
        # manifest object item_type (open context items)
        models_utils.validate_related_manifest_item_type(
            man_obj=self.item,
            allowed_types=configs.OC_ITEM_TYPES,
            obj_role='item'
        )
        super(AllIdentifier, self).save(*args, **kwargs)

    def __str__(self):
        out = (
            f'{self.uuid}: {self.item.label} [{self.item.uuid}] '
            f'-> {self.scheme}: {self.id} [{self.rank}] -> '
        )
        return out


    class Meta:
        db_table = 'oc_all_identifiers'
        unique_together = (
            (
                "item",
                "scheme",
                "rank",
            ),
            (
                "scheme",
                "id",
            ),
        )
        ordering = ["item", "rank", "scheme",]
        default_related_name = 'identifiers'


class ManifestCachedSpacetime(models.Model):
    """Model mapped to the oc_all_manifest_best_spacetime view.
    
    NOTE: This only works with items that have geospatial or
    chronological information directly associated with a given item
    or an item's context. This means "subjects" and "projects" item_types
    are more likely to have geospatial data accessible in this way.

    For other item types (esp. "media" and "documents"), one will first
    need to look up a related "subject" item from the AllAssertion model,
    and use that to look up the best space time objects.
    
    """

    item = models.OneToOneField(
        AllManifest,
        db_column='item_uuid',
        primary_key=True,
        on_delete=models.DO_NOTHING,
        related_name='best_spacetime',
    )
    # geo_source_uuid = models.UUIDField(null=True)
    geo_source = models.ForeignKey(
        AllManifest,
        db_column='geo_source_uuid',
        related_name='manifest_geo_source',
        on_delete=models.DO_NOTHING,
        null=True,
    )
    # geo_spacetime_uuid = models.UUIDField(null=True)
    geo_spacetime = models.ForeignKey(
        AllSpaceTime,
        db_column='geo_spacetime_uuid',
        related_name='spacetime_geo',
        on_delete=models.DO_NOTHING,
        null=True,
    )
    geo_depth = models.IntegerField(null=True)
    geometry_type = models.TextField(null=True)
    geometry = JSONField(null=True)
    latitude = models.DecimalField(max_digits=24, decimal_places=21, null=True)
    longitude = models.DecimalField(max_digits=24, decimal_places=21, null=True)
    geo_specificity = models.IntegerField(null=True)

    # chrono_source_uuid = models.UUIDField(null=True)
    chrono_source = models.ForeignKey(
        AllManifest,
        db_column='chrono_source_uuid',
        related_name='manifest_chrono_source',
        on_delete=models.DO_NOTHING,
        null=True,
    )
    # chrono_spacetime_uuid = models.UUIDField(null=True)
    chrono_spacetime = models.ForeignKey(
        AllSpaceTime,
        db_column='chrono_spacetime_uuid',
        related_name='spacetime_chrono',
        on_delete=models.DO_NOTHING,
        null=True,
    )
    chrono_depth = models.IntegerField(null=True)
    earliest = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    start = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    stop = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    latest = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    reference_type = models.TextField(null=True)

    class Meta:
        managed = False
        db_table = 'oc_all_manifest_cached_spacetime'

    def __str__(self):
        return (
            f'Best spacetime for {self.item_id} '
            f'(lat: {self.latitude}, lon: {self.longitude}); '
            f'{self.earliest} to {self.latest}'
        )


def refresh_cached_spacetime_view():
    """Refresh the materialized view for cached spacetime data"""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY oc_all_manifest_cached_spacetime;"
        )