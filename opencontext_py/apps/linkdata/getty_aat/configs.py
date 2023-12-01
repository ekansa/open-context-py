GETTY_AAT_VOCAB_URI = 'https://vocab.getty.edu/aat'
GETTY_AAT_BASE_URI = 'vocab.getty.edu/aat/'

# These are the top-level hierarchies in the AAT, in Open Context
# these should all be child vocabularies of the AAT vocabulary.
GETTY_AAT_FACET_DICT_LIST = [
    {
        'id': 'vocab.getty.edu/aat/300264086',
        'label': 'Associated Concepts Facet',
    },
    {
        'id': 'vocab.getty.edu/aat/300264087',
        'label': 'Physical Attributes Facet',
    },
    {
        'id': 'vocab.getty.edu/aat/300264088',
        'label': 'Styles and Periods Facet',
    },
    {
        'id': 'vocab.getty.edu/aat/300264089',
        'label': 'Agents Facet',
    },
    {
        'id': 'vocab.getty.edu/aat/300264090',
        'label': 'Activities Facet',
    },
    {
        'id': 'vocab.getty.edu/aat/300264091',
        'label': 'Materials Facet',
    },
    {
        'id': 'vocab.getty.edu/aat/300264092',
        'label': 'Objects Facet',
    },
    {
        'id': 'vocab.getty.edu/aat/300343372',
        'label': 'Brand Names Facet',
    },
]

# The list of AAT facet URIs.
GETTY_AAT_FACET_URI_LIST = [f.get('id') for f in GETTY_AAT_FACET_DICT_LIST]


# This are the preferred parent uris that all children should belong to
AAT_PREFERRED_PARENT_URI_LIST = [
    # Order from most specific to most general and abstract.
    'vocab.getty.edu/aat/300010900', # Metal
    'vocab.getty.edu/aat/300010360', # Inorganic material
    'vocab.getty.edu/aat/300265629', # Biological material
    'vocab.getty.edu/aat/300386879', # ceramic ware (visual works)
    'vocab.getty.edu/aat/300053001', # Processes and Techniques (hierarchy name)
    'vocab.getty.edu/aat/300226816', # form attributes
    'vocab.getty.edu/aat/300010269', # positional attributes
    'vocab.getty.edu/aat/300191817', # fabrication attributes
    'vocab.getty.edu/aat/300010357', # materials (substances)

    'vocab.getty.edu/aat/300045611', # Containers (hierarchy name)
    'vocab.getty.edu/aat/300209261', # Costume (hierarchy name)
    'vocab.getty.edu/aat/300037221', # Exchange Media (hierarchy name)
    'vocab.getty.edu/aat/300037335', # Furnishings (hierarchy name)
    'vocab.getty.edu/aat/300026029', # Information Forms (hierarchy name)
    'vocab.getty.edu/aat/300207851', # Measuring Devices (hierarchy name)
    'vocab.getty.edu/aat/300136012', # Recreational Artifacts (hierarchy name)
    'vocab.getty.edu/aat/300041619', # Sound Devices (hierarchy name)
    'vocab.getty.edu/aat/300022238', # Tools and Equipment (hierarchy name)
    'vocab.getty.edu/aat/300036743', # Weapons and Ammunition (hierarchy name)
    'vocab.getty.edu/aat/300264552', # Visual Works (hierarchy name)
    'vocab.getty.edu/aat/300264550', # Built Environment (hierarchy name)
    'vocab.getty.edu/aat/300241490', # Components (hierarchy name)
    'vocab.getty.edu/aat/300015646', # Styles and Periods (hierarchy name)
    'vocab.getty.edu/aat/300055126', # Associated Concepts (hierarchy name)
    'vocab.getty.edu/aat/300054134', # Disciplines (hierarchy name),
    'vocab.getty.edu/aat/300185711', # Object Genres (hierarchy name)
    'vocab.getty.edu/aat/300264092', # Objects Facet
]

AAT_PREFERRED_URI_TO_PARENT_URI_DICT = {
    # <attributes and properties by specific type> ->
    'vocab.getty.edu/aat/300226808': 'vocab.getty.edu/aat/300123559',
    # Metalworking process, techique -> Metal
    'vocab.getty.edu/aat/300053900': 'vocab.getty.edu/aat/300010900',
    # Organic material -> materials (substances)
    'vocab.getty.edu/aat/300265630': 'vocab.getty.edu/aat/300010357',
    # Peaked caps -> costume
    'vocab.getty.edu/aat/300391049': 'vocab.getty.edu/aat/300209261',
    # Object groupings -> vocab.getty.edu/aat/300241490
    'vocab.getty.edu/aat/300404444': 'vocab.getty.edu/aat/300241490',
    # Liturgical containers -> Containers
    'vocab.getty.edu/aat/300391124': 'vocab.getty.edu/aat/300045611',
    # Organism by condition -> Object
    'vocab.getty.edu/aat/300390503': 'vocab.getty.edu/aat/300185711',
    # metal by product -> Object
    'vocab.getty.edu/aat/300011055': 'vocab.getty.edu/aat/300185711',
    # Military patches -> Information Forms (hierarchy name)
    'vocab.getty.edu/aat/300391047': 'vocab.getty.edu/aat/300026029',
    # Chin straps -> Costume (hierarchy name)
    'vocab.getty.edu/aat/300391056': 'vocab.getty.edu/aat/300209261',
    # Silicates -> Inorganic
    'vocab.getty.edu/aat/300246922': 'vocab.getty.edu/aat/300010360',
    # Silicates -> Inorganic
    'vocab.getty.edu/aat/300246922': 'vocab.getty.edu/aat/300010360',
    # Soil -> Material
    'vocab.getty.edu/aat/300206579': 'vocab.getty.edu/aat/300010357',
    # combo inorganic or organic
    'vocab.getty.edu/aat/300212963': 'vocab.getty.edu/aat/300265629',
    # Gold -> metal
    'vocab.getty.edu/aat/300011021': 'vocab.getty.edu/aat/300010900',
    # Food -> Biological material
    'vocab.getty.edu/aat/300254496': 'vocab.getty.edu/aat/300265629',
    # Rhyta -> ceramic ware
    'vocab.getty.edu/aat/300198841': 'vocab.getty.edu/aat/300045611',
}