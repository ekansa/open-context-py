
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


def get_spacetime_geo_and_chronos(rel_subjects_man_obj):
    """Gets space time objects for a manifest_obj and parent contexts"""
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
        'event'
    ).select_related( 
        'event_class'
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
    
    if not len(act_geos):
        # We found no geometries, so return None
        return None
    
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




def add_geojson_features(item_man_obj, rel_subjects_man_obj=None, act_dict=None):
    """Adds GeoJSON feature (with when object) to the act_dict
    
    :param AllManifest item_man_obj: The manifest object getting a
        GeoJSON representation
    :param AllManifest rel_subjects_man_obj: A manifest object with item_type
        "subjects" that itself (or it's parent context) will be the source
        of spacetime data for the item_man_obj.
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
        properties["type"] = rep_utils.get_item_key_or_uri_value(spacetime_obj.event_class)
        if str(spacetime_obj.event.uuid) != configs.DEFAULT_EVENT_UUID:
            # We have a non-standard event for this feature, so update the feature id.
            feature["id"] = f'#-event-{spacetime_obj.event.slug}'
            properties["label"] = spacetime_obj.event.label
        if item_man_obj == spacetime_obj.item and spacetime_obj.geometry_type:
            # This spacetime object has it's own geometry, and that geometry
            # is associated directly to the item_man_obj for which we're building a
            # GeoJSON representation.
            properties["reference-type"] = "specified"
            feature["geometry"] = spacetime_obj.geometry.copy()
            feature["geometry"]["id"] = f"#feature-geom-{spacetime_obj.uuid}"
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
            properties["reference-type"] = "inferred"
            properties["reference-uri"] = f"https://{ref_spacetime_obj.item.uri}"
            properties["reference-label"] = ref_spacetime_obj.item.label
            properties["reference-slug"] = ref_spacetime_obj.item.slug
            if ref_spacetime_obj.geometry_type != "Point":
                properties["contained-in-region"] = True
                properties["location-region-note"] = "This point represents the center of the region containing this item."
            else:
                properties["contained-in-region"] = False
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
            when["reference-type"] = "specified"
        else:
            when["reference-type"] = "inferred"
            when["reference-uri"] = f"https://{chrono_spacetime_obj.item.uri}"
            when["reference-label"] = chrono_spacetime_obj.item.label
            when["reference-slug"] = chrono_spacetime_obj.item.slug

        feature["when"] = when
        features.append(feature)
    
    act_dict["features"] = features
    return act_dict