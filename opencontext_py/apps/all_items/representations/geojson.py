
import copy
import hashlib
import uuid as GenUUID

from django.core.cache import caches
from django.db.models import OuterRef, Subquery

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.isoyears import ISOyears

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import rep_utils


# List of URIs for gazetteer vocabularies to help identify
# non-subjects manifest entities that may have spacetime objects.
GAZETTEER_VOCAB_URIS = [
    'www.geonames.org',
    'pleiades.stoa.org',
]

DEFAULT_LOCATION_NOTE = (
    'Location data available with no intentional reduction in precision, '
    'and no documented estimates of precision or accuracy.'
)
DEFAULT_LOCATION_LOW_PRECISION_NOTE = (
    'Location data has known limits on precision and/or accuracy.'
)
DEFAULT_LOCATION_SECURITY_NOTE = 'Location data approximated as a security precaution.'


def get_spacetime_geo_and_chronos(rel_subjects_man_obj, require_geo=True):
    """Gets space time objects for a manifest_obj and parent contexts
    
    :param AllManifest rel_subjects_man_obj: The related manifest item
        that will hopefully have associated (either directly or through
        contexts) geospatial and chronology data.
    :param bool require_geo: If True, return None if there is no
        geospatial data to return. If False, allow return of chronology
        absent geospatial data.
    """
    if not rel_subjects_man_obj:
        return None
    if (rel_subjects_man_obj.item_type != 'subjects'
        and rel_subjects_man_obj.context.uri not in GAZETTEER_VOCAB_URIS):
        return None
    context_objs = [rel_subjects_man_obj]
    # Get a list of all the context objects in this manifest_obj
    # hierarchy.
    act_man_obj = rel_subjects_man_obj
    while (act_man_obj.context.item_type == 'subjects' 
       and str(act_man_obj.context.uuid) 
       not in configs.DEFAULT_SUBJECTS_ROOTS):
        context_objs.append(act_man_obj.context)
        act_man_obj = act_man_obj.context
    
    # Now use these context objects to query for space time objects
    spacetime_qs = AllSpaceTime.objects.filter(
        item__in=context_objs,
    ).select_related(
        'item'
    ).select_related(
        'item__project'
    ).select_related(
        'event'
    ).select_related( 
        'event__item_class'
    )
    if not len(spacetime_qs):
        # We found no spacetime objects at all. Distressing, but possible
        # if we're still preparing a dataset for publication.
        return None

    act_spacetime_features = [] # List of features with both geometries and chronology.
    act_geos = [] # List of spacetime objects with only geometry 
    act_chronos = [] # List of spacetime objects with only chronology

    # Interate through the list of context_objs. These are ordered from most
    # specific to most general, all the way up to world regions. This will select
    # the spacetime objects with the most specific geometries and chronologies
    for context_obj in context_objs:
        for spacetime_obj in spacetime_qs:
            spacetime_obj.inherit_chrono = None
            spacetime_obj.inherit_geometry = None
            if context_obj != spacetime_obj.item:
                continue
            if (
                context_obj == rel_subjects_man_obj
                and spacetime_obj.geometry_type 
                and spacetime_obj.start is not None and spacetime_obj.stop is not None
            ):
                # We have both geometry and chronology for the specific 
                # item specified in rel_subjects_man_obj
                act_spacetime_features.append(spacetime_obj)
            if spacetime_obj.geometry_type:
                # This spacetime obj contains a geometry
                if context_obj == rel_subjects_man_obj or len(act_geos) == 0:
                    act_geos.append(spacetime_obj)
            if spacetime_obj.start is not None and spacetime_obj.stop is not None:
                # This spacetime obj contains a time span
                if context_obj == rel_subjects_man_obj or len(act_chronos) == 0:
                    act_chronos.append(spacetime_obj)
        if len(act_spacetime_features):
            # Our work is done here, the rel_subjects_man_obj has specific
            # geometry and chronology spacetime features. So skip out
            # and return those, because we don't have to mess with inherited
            # geometries or time-spans.
            return act_spacetime_features
        if len(act_geos) and len(act_chronos):
            # We have everything we need to end this looping.
            break
    
    if require_geo and not len(act_geos):
        # We found no geometries, so return None
        return None
    if not require_geo and not len(act_geos) and len(act_chronos):
        # We found some chronology data, so return the chronology
        # absent the geospatial.
        return act_chronos
    
    inherit_chrono = None
    if len(act_chronos):
        # This is the spacetime object that we use for
        # inherited time spans
        inherit_chrono = act_chronos[0]
    
    if len(act_geos) > len(act_chronos):
        # We have multiple geometries, which means we need
        # to inherit a timespan (which may be None)
        for spacetime_obj in act_geos:
            spacetime_obj.inherit_chrono = inherit_chrono
            act_spacetime_features.append(spacetime_obj)
        return  act_spacetime_features
    elif len(act_chronos) > len(act_geos):
        # We have multiple timespans, which means we need
        # to inherit the geometry
        for spacetime_obj in act_geos:
            spacetime_obj.inherit_geometry = act_geos[0]
            act_spacetime_features.append(spacetime_obj)
        return  act_spacetime_features
    
    # A case where there's only 1 geometry and we need
    # to add an inherited chronology spacetime object.
    spacetime_obj = act_geos[0]
    spacetime_obj.inherit_chrono = inherit_chrono
    return [
        spacetime_obj
    ]


def get_meta_json_value_from_item_hierarchy(item_man_obj, meta_json_key='geo_note', default=None):
    """Gets a value from a key in the meta_json field up a hierarchy of inheritance

    :param AllManifest item_man_obj: An instance of the AllManifest model
        that is getting geospatial data.
    :param str meta_json_key: A string meta_json key to lookup
    :param * default: the default value to return if a key lookup fails
    """
    key_val = item_man_obj.meta_json.get(
        meta_json_key,
        item_man_obj.project.meta_json.get(
            meta_json_key,
        )
    )
    if not key_val and str(item_man_obj.project.project.uuid) != configs.OPEN_CONTEXT_PROJ_UUID:
        key_val = item_man_obj.project.project.meta_json.get(
            meta_json_key,
            default,
        )
    return key_val


def add_precision_properties(properties, item_man_obj, spacetime_obj, for_solr=False):
    """Adds geospatial precision notes

    :param dict properties: A GeoJSON properties dictionary.
    :param AllManifest item_man_obj: An instance of the AllManifest model
        that is getting geospatial data.
    :param AllSpaceTime spacetime_obj: A spacetime object with location
        precision information
    :param bool for_solr: A boolean flag to add additional metadata because
        the dict will be used for solr indexing.
    """

    # First, attempt to get a geospatial precision note from the item
    # itself, or the project for this item, or this item's project__project!
    item_precision_specificity = get_meta_json_value_from_item_hierarchy(
        item_man_obj, 
        meta_json_key='geo_specificity', 
        default=0
    )
    item_precision_note = get_meta_json_value_from_item_hierarchy(
        item_man_obj, 
        meta_json_key='geo_note', 
        default=None
    )

    # If we don't have an item precision note for this item (including
    # parent projects, use the note associated with the spatial inference)
    if not item_precision_note and spacetime_obj.item.uuid != item_man_obj.uuid:
        item_precision_note = spacetime_obj.item.meta_json.get(
            'geo_note',
            spacetime_obj.item.project.meta_json.get(
                'geo_note',
            )
        )
    if not item_precision_note:
        item_precision_note = None

    
    if spacetime_obj.geo_specificity and spacetime_obj.geo_specificity != 0:
        # Use the geo specificity actually from the geo data.
        item_precision_specificity = spacetime_obj.geo_specificity

    if not item_precision_specificity:
        item_precision_specificity = 0
    
    if item_precision_specificity == 0:
        # Case of no known attempt to obscure location data, no statement
        # about any uncertainty.
        if item_precision_note:
            properties["location_precision_note"] = item_precision_note
        else:
            properties["location_precision_note"] = DEFAULT_LOCATION_NOTE
    elif item_precision_specificity < 0:
        # Case of intentionally obscured location data.
        properties["location_precision_factor"] = abs(item_precision_specificity)
        if item_precision_note:
            properties["location_precision_note"] = item_precision_note
        else:
            properties["location_precision_note"] = DEFAULT_LOCATION_SECURITY_NOTE

        properties["location_precision_factor"] = abs(item_precision_specificity)
    elif item_precision_specificity > 0:
        # Case of otherwise uncertain / low precision location data.
        properties["location_precision_factor"] = abs(item_precision_specificity)
        if item_precision_note:
            properties["location_precision_note"] = item_precision_note
        else:
            properties["location_precision_note"] = DEFAULT_LOCATION_LOW_PRECISION_NOTE

        properties["location_precision_factor"] = abs(item_precision_specificity)
    else:
        pass

    if for_solr:
        # Always make sure we have the location precision factor
        properties["location_precision_factor"] = abs(item_precision_specificity)
        properties["event_id"] = str(spacetime_obj.event.uuid)
        properties["event__item_class_id"] = str(spacetime_obj.event.item_class.uuid)
        properties["event__item_class__slug"] = spacetime_obj.event.item_class.slug
        if spacetime_obj.latitude and spacetime_obj.latitude:
            properties["latitude"] = float(spacetime_obj.latitude)
            properties["longitude"] = float(spacetime_obj.longitude)
    return properties


def add_geojson_features(item_man_obj, rel_subjects_man_obj=None, act_dict=None, for_solr=False):
    """Adds GeoJSON feature (with when object) to the act_dict
    
    :param AllManifest item_man_obj: The manifest object getting a
        GeoJSON representation
    :param AllManifest rel_subjects_man_obj: A manifest object with item_type
        "subjects" that itself (or it's parent context) will be the source
        of spacetime data for the item_man_obj.
    :param bool for_solr: A boolean flag to add additional metadata because
        the dict will be used for solr indexing.
    """
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    
    if not rel_subjects_man_obj:
        if item_man_obj.item_type == "subjects":
            # We're describing a subjects item, so the rel_subjects_man_obj
            # is the same manifest object.
            rel_subjects_man_obj = item_man_obj
        elif item_man_obj.item_type == "uri" and item_man_obj.context.uri in GAZETTEER_VOCAB_URIS:
            # We're describing a geonames place item.
            rel_subjects_man_obj = item_man_obj
    
    # Get the spacetime features for this rel_subjects_man_obj.
    act_spacetime_features = get_spacetime_geo_and_chronos(rel_subjects_man_obj)
    if not act_spacetime_features:
        # No geomtries found in the whole context hierarchy, so 
        # no geojson to add.
        return act_dict
    # We have features to add.
    act_dict["type"] = "FeatureCollection"
    features = []
    for spacetime_obj in act_spacetime_features:
        feature_id = spacetime_obj.feature_id
        if feature_id <= len(features):
            feature_id = len(features) + 1
        feature = LastUpdatedOrderedDict()
        feature["type"] = "Feature"
        feature["id"] = f"#feature-{feature_id}"
        properties = LastUpdatedOrderedDict()
        properties["id"] = f"#feature-props-{feature_id}"
        properties["href"] = f"https://{item_man_obj.uri}"
        properties["type"] = rep_utils.get_item_key_or_uri_value(spacetime_obj.event.item_class)
        if str(spacetime_obj.event.uuid) != configs.DEFAULT_EVENT_UUID:
            # We have a non-standard event for this feature, so update the feature id.
            feature["id"] = f'#-event-{spacetime_obj.event.slug}'
            properties["label"] = spacetime_obj.event.label
        if item_man_obj == spacetime_obj.item and spacetime_obj.geometry_type:
            # This spacetime object has it's own geometry, and that geometry
            # is associated directly to the item_man_obj for which we're building a
            # GeoJSON representation.
            properties["reference_type"] = "specified"
            # Add the location precision note.
            properties = add_precision_properties(
                properties, 
                item_man_obj, 
                spacetime_obj,
                for_solr=for_solr,
            )
            feature["geometry"] = spacetime_obj.geometry.copy()
            feature["geometry"]["id"] = f"#feature-geom-{spacetime_obj.uuid}"
            if for_solr:
                properties["reference_uri"] = f"https://{spacetime_obj.item.uri}"
                properties["reference_label"] = spacetime_obj.item.label
                properties["reference_slug"] = spacetime_obj.item.slug
        else:
            # We need to do some inferencing to add geospatial data.
            ref_spacetime_obj = spacetime_obj
            if not spacetime_obj.geometry_type:
                # We need to use a spacetime object related via inheritance. 
                ref_spacetime_obj = getattr(spacetime_obj, 'inherit_geometry', None)
                print('we are here')
                print(spacetime_obj.__dict__)
            if not ref_spacetime_obj:
                # We don't have any geometry of any source. This should never
                # happen so just continue.
                continue

            # This spacetime object has geometry intereted from another spacetime
            # object. We only do Point inheritance however.
            properties["reference_type"] = "inferred"
            properties["reference_uri"] = f"https://{ref_spacetime_obj.item.uri}"
            properties["reference_label"] = ref_spacetime_obj.item.label
            properties["reference_slug"] = ref_spacetime_obj.item.slug
            if ref_spacetime_obj.geometry_type != "Point":
                properties["contained_in_region"] = True
                properties["location_region_note"] = "This point represents the center of the region containing this item."
            else:
                properties["contained_in_region"] = False
            
            # Add the location precision note.
            properties = add_precision_properties(
                properties, 
                item_man_obj, 
                ref_spacetime_obj,
                for_solr=for_solr,
            )

            geomtry = LastUpdatedOrderedDict()
            geomtry["id"] = f"#geo-geom-{ref_spacetime_obj.uuid}"
            geomtry["type"] = "Point"
            geomtry["coordinates"] = [
                float(ref_spacetime_obj.longitude),
                float(ref_spacetime_obj.latitude),
            ]
            feature["geometry"] = geomtry

        feature["properties"] = properties

        # Now check if we have chronology to add.
        chrono_spacetime_obj = spacetime_obj
        if chrono_spacetime_obj.earliest is None:
            chrono_spacetime_obj = getattr(spacetime_obj, 'inherit_chrono', None)
            if chrono_spacetime_obj is not None and chrono_spacetime_obj.earliest is None:
                chrono_spacetime_obj = None

        if not chrono_spacetime_obj:
            # We don't have any chronology to add, so skip that part
            features.append(feature)
            continue
    
        # Add the chronology object.
        when = LastUpdatedOrderedDict()
        when["id"] = f"#feature-when-{chrono_spacetime_obj.uuid}"
        when["start"] = ISOyears().make_iso_from_float(
            float(chrono_spacetime_obj.earliest)
        )
        when["stop"] = ISOyears().make_iso_from_float(
            float(chrono_spacetime_obj.latest)
        )
        if chrono_spacetime_obj.item == item_man_obj:
            when["reference_type"] = "specified"
        else:
            when["reference_type"] = "inferred"
            when["reference_uri"] = f"https://{chrono_spacetime_obj.item.uri}"
            when["reference_label"] = chrono_spacetime_obj.item.label
            when["reference_slug"] = chrono_spacetime_obj.item.slug

        if for_solr:
            when["earliest"] = float(chrono_spacetime_obj.earliest)
            when["latest"] = float(chrono_spacetime_obj.latest)
            when["reference_uri"] = f"https://{chrono_spacetime_obj.item.uri}"
            when["reference_label"] = chrono_spacetime_obj.item.label
            when["reference_slug"] = chrono_spacetime_obj.item.slug 

        feature["when"] = when
        features.append(feature)
    
    act_dict["features"] = features
    return act_dict