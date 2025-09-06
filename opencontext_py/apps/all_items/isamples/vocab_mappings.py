
import datetime
import hashlib
import json
import uuid as GenUUID



import duckdb
from duckdb.typing import *

from django.conf import settings


from opencontext_py.libs import duckdb_con



# iSamples Material Sample Object Type Vocabulary
"""
┌────────────────────────────────────┬────────┐
│          item_class_label          │  cnt   │
│              varchar               │ int64  │
├────────────────────────────────────┼────────┤
│ Animal Bone                        │ 506342 │
│ Object                             │ 206883 │
│ Radiocarbon Sample                 │ 166959 │
│ Sample                             │  78315 │
│ Plant remains                      │  42978 │
│ Architectural Element              │  23272 │
│ Pottery                            │  22158 │
│ Sample, Collection, or Aggregation │   9131 │
│ Shell                              │   5554 │
│ Human Bone                         │   3736 │
│ Non Diagnostic Bone                │   1332 │
│ Glass                              │   1232 │
│ Bulk Ceramic                       │   1160 │
│ Coin                               │   1062 │
│ Bulk Lithic                        │    681 │
│ Biological record                  │    321 │
│ Groundstone                        │    272 │
│ Sculpture                          │     75 │
│ Bone grouping                      │     26 │
│ Reference Collection               │     18 │
├────────────────────────────────────┴────────┤
│ 21 rows                           2 columns │
"""

MAP_ITEM_CLASS_LABEL_MATERIAL_SAMPLE_OBJECT_TYPES = {
    'Animal Bone': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/organismpart',
        'label': 'Organism part',
        'scheme_name': 'iSamples Material Sample Object Type Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/conceptscheme',
        'description': (
            'Material sample that is part of an organism, e.g. a tissue sample, plant leaf, '
            'flower, bird feather. Include internal parts not composed of organic material '
            '(e.g. teeth, bone), and hard body parts that are not shed (hoof, horn, tusk, claw). '
            'Not fossilized; generally includes organism parts native to deposits of '
            'Holocene to Recent age.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Object': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
        'label': 'Artifact',
        'scheme_name': 'iSamples Material Sample Object Type Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/conceptscheme',
        'description': (
            'An object made (manufactured, shaped, modified) by a human being, or precursor hominid. '
            'Include a set of pieces belonging originally to a single object and treated as a '
            'single sample.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Radiocarbon Sample': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/biologicalmaterialsample',
        'label': 'Biological material sample',
        'scheme_name': 'iSamples Material Sample Object Type Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/conceptscheme',
        'description': (
            'Material sample representative of one or more living organisms from a '
            'particular biome context, megascopic or microscopic'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Sample': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/materialsample',
        'label': 'Material sample',
        'scheme_name': 'iSamples Material Sample Object Type Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/conceptscheme',
        'description': (
            'A material entity that represents an entity of interest in whole or in part '
            'Top concept in material sample object type hierarchy. Represents any material sample object.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Plant remains': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/biologicalmaterialsample',
    },
    'Architectural Element': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/materialsample',
    },
    'Pottery': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Sample, Collection, or Aggregation': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/materialsample',
    },
    'Shell': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/organismproduct',
        'label': 'Organism product',
        'scheme_name': 'iSamples Material Sample Object Type Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/conceptscheme',
        'description': (
            'Material sample is a thing produced by some organism, generally not composed of organic '
            'material or including biological tissue, e.g. Shell, antler, egg shell, coral skeleton '
            '(organic tissue not included), fecal matter, cocoon, web. Consider internal parts not '
            'composed of organic material (e.g. teeth, bone) and hard body parts that are not shed '
            '(hoof, horn, tusk) to be organism parts.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Human Bone': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/organismpart',
    },
    'Non Diagnostic Bone': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/organismpart',
    },
    'Glass': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Bulk Ceramic': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Coin': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Bulk Lithic': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Lithic': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Biological record': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/biologicalmaterialsample',
    },
    'Groundstone': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Sculpture': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/artifact',
    },
    'Bone grouping': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/organismpart',
    },
    'Reference Collection': {
        'pid': 'https://w3id.org/isample/vocabulary/materialsampleobjecttype/1.0/materialsample',
    },  
}


MAP_ITEM_CLASS_LABEL_MATERIAL_TYPES = {
    'Animal Bone': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/biogenicnonorganicmaterial',
        'label': 'Biogenic non-organic material',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Material produced by an organism but not composed of **very large molecules of '
            'biological origin.** E.g. bone, tooth, shell, coral skeleton.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Object': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/material',
        'label': 'Material',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Top Concept in iSamples Material Category scheme'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Radiocarbon Sample': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/organicmaterial',
        'label': 'Organic material',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Material derived from living organisms and composed primarily of one or more very '
            'large molecules of biological origin. Examples: body (animal or plant), body part, '
            'fecal matter, seeds, wood, tissue, biological fluids, biological waste, algal '
            'material, biofilm, necromass, plankton.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Sample': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/material',
    },
    'Plant remains': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/organicmaterial',
    },
    'Architectural Element': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/material',
    },
    'Pottery': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/otheranthropogenicmaterial',
        'label': 'Other anthropogenic material',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Non-metallic material produced by human activity. Organic products of agricultural '
            'activity are both anthropogenic and organic. Include lab preparations like XRF '
            'pellet and rock powders. Examples: ceramics, concrete, slag, (anthropogenic) glass, '
            'mine tailing, plaster, waste.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Sample, Collection, or Aggregation': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/material',
    },
    'Shell': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/biogenicnonorganicmaterial',
    },
    'Human Bone': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/biogenicnonorganicmaterial',
    },
    'Non Diagnostic Bone': {
       'pid': 'https://w3id.org/isample/vocabulary/material/1.0/biogenicnonorganicmaterial',
    },
    'Glass': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/otheranthropogenicmaterial',
    },
    'Bulk Ceramic': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/otheranthropogenicmaterial',
    },
    'Coin': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/anthropogenicmetal',
        'label': 'Anthropogenic metal material',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Metal that has been produced or used by humans. Samples of naturally occurring '
            'metallic material (e.g. native copper, gold nuggets) should be considered '
            'mineral material.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Bulk Lithic': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/rock',
        'label': 'Rock',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Consolidated aggregate of particles (grains) of rock, mineral (including '
            'native elements), mineraloid, or solid organic material.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Lithic': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/rock',
    },
    'Biological record': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/material',
    },
    'Groundstone': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/rock',
    },
    'Sculpture': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/material',
    },
    'Bone grouping': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/biogenicnonorganicmaterial',
    },
    'Reference Collection': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/material',
    },

    # Below are other material types in the isamples vocabulary, but these don't correspond
    # to the item_class_label in Open Context. We have these below to help populate the
    # the iSamples PQG table.
    'Mixed soil sediment or rock': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/mixedsoilsedimentrock',
        'label': 'Mixed soil sediment or rock',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Material is mixed aggregation of fragments of undifferentiated soil, sediment or '
            'rock origin. e.g. cuttings from some boreholes (rock fragments and caved soil or sediment).'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Mineral': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/mineral',
        'label': 'Mineral',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Material consists of a single mineral or mineraloid phase.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Natural Solid Material': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/earthmaterial',
        'label': 'Natural Solid Material',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'A naturally occurring solid material that is not anthropogenic, biogenic, or ice.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Sediment': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/sediment',
        'label': 'Sediment',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Solid granular material transported by wind, water, or gravity, not modified by '
            'interaction with biosphere or atmosphere (to differentiate from soil).'
        ),
        'otype': 'IdentifiedConcept',
    },
    'Rock or sediment': {
        'pid': 'https://w3id.org/isample/vocabulary/material/1.0/rockorsediment',
        'label': 'Rock or sediment',
        'scheme_name': 'iSamples Materials Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/material/1.0/materialsvocabulary',
        'description': (
            'Material is rock or sediment'
        ),
        'otype': 'IdentifiedConcept',
    },
}



MAP_SITE_TYPE_SAMPLED_SITE_TYPES = {
    'region': {
        'pid': 'https://w3id.org/isample/vocabulary/sampledfeature/1.0/earthsurface',
        'label': 'Earth surface',
        'scheme_name': 'iSamples Sampled Feature Type Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/sampledfeature/1.0/sampledfeaturevocabulary',
        'description': (
            'Sampled feature is the interface between solid earth and hydrosphere or atmosphere. '
            'Includes samples representing things collected on the surface, in the uppermost part '
            'of the material below the surface, or air or water directly at the contact with the '
            'Earth surface.'
        ),
        'otype': 'IdentifiedConcept',
    },
    'site': {
        'pid': 'https://w3id.org/isample/vocabulary/sampledfeature/1.0/pasthumanoccupationsite',
        'label': 'Site of past human activities',
        'scheme_name': 'iSamples Sampled Feature Type Vocabulary',
        'scheme_uri': 'https://w3id.org/isample/vocabulary/sampledfeature/1.0/sampledfeaturevocabulary',
        'description': (
            'Sampled feature  is a place where humans have been and left evidence of their activity. '
            'Includes prehistoric and paleo hominid sites.'
        ),
        'otype': 'IdentifiedConcept',
    },
}