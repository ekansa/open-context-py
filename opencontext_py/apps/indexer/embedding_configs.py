
QUERY_PARTS = [
    '"Element" can describe anatomy. "Family" and "order" can be biological classification. ',
    'Used with pottery, the words "fabric" and "ware" can describe ceramic material.',
    '"Excavation Unit", "Locus", "Lot", and "Unit" typically mean archaeological context.',
    'Architecture, walls, floors, pits, ditches, hearths, ovens, and dumps can be features.',
]

# This still fits in the max token length
QUERY_PART = '\n'.join(QUERY_PARTS)

# Add some additional context information to the strings that get made into
# embeddings. Hopefully this will help make "vibe-searches" more sensible!
CLASS_EXPLAIN_DICT = {
    "Animal Bone": """
    This is about animal bone. The word "element" describes anatomy, not a chemical.
    """,
    "Human Bone": """
    This is about human bone. The word "element" describes anatomy, not a chemical.
    """,
    "Plant remains": """
    This is about plant remains. The words "family" and "order" describe biological taxonomy.
    """,
    "Region": """
    This is about a geographic region.
    """,
    "Object": """
    This is about an archaeological artifact.
    """,
    "Coin": """
    This is about an archaeological artifact, usually made of metal, and likely used as currency.
    """,
    "Pottery": """
    This is about an archaeological artifact made of ceramic material.
    This may be a fragmented sherd (shard) or more or less complete and intact vessel.
    The words "fabric" and "ware" describe ceramic material.
    """,
    "Glass": """
    This is about an archaeological artifact made of glass.
    """,
    "Groundstone": """
    This is about an archaeological artifact made of rock, that was shaped by grinding and polishing.
    """,
    "Architectural Element": """
    This is about an component of a building, including decorative features.
    """,
    "Non Diagnostic Bone": """
    This is about bone remains that lack identifying characteristics.
    """,
    "Survey Unit": """
    This is about an area of the Earth"s surface studied for indications of human activity in the past.
    """,
    "Site": """
    This is about a place with indications of human activity in the past. 
    """,
    "Site Area": """
    This is about a part of an archaeological site. 
    A site is a place with indications of human activity in the past. 
    "Site Area", "Area", "Operation", and "Field Project" have similar meanings.
    """,
    "Context": """
    This is about a place that contained or contains physical remains studied by archaeologists. 
    Place, the type of soil, depth, coordinates, stratigraphic layer are often aspects of context. 
    """,
    "Feature": """
    This is about archaeologically observed physical modifications of a place, especially an area of ground.
    Remains of architecture, like walls and floors, but also pits, ditches, hearths, ovens, and dumps can be features.
    """,
    "Structure": """
    This is about a part of architecture or a building. It is an archaeological feature.
    """,
    "Space": """
    This is about a zone or part of architecture or a building. It is an archaeological context.
    """,
    "Excavation Unit": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Locus": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Lot": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Basket": """
    This is about a collection of material from a given archaeological context such as an "Excavation Unit", "Locus", "Lot", or "Unit".
    """,
    "Area": """
    This is about a part of an archaeological site. 
    A site is a place with indications of human activity in the past. 
    "Site Area", "Area", "Operation", and "Field Project" have similar meanings.
    """,
    "Trench": """
    This is about an excavated part of an archaeological site. 
    A trench may contain many different excavated contexts, and each context may be called an "Excavation Unit", "Locus", "Lot", or "Unit". 
    """,
    "Square": """
    This is about a geometrically defined part of an archaeological site. 
    A square is used to help archaeologists to help record the locations of features, deposits, contexts, artifacts, etc. 
    """,
    "Unit": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Sequence": """
    This is about a stratigraphic layer. It is an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    """,
    "Stratum": """
    This is about a stratigraphic layer. It is an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    """,
    "Phase": """
    This is about a stratigraphic layer. It is an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    """,
    "Mound": """
    This is about a hill-like part of an archaeological site.
    """,
    "Sample": """
    This is about a very general physical thing collected for study and analysis.
    """,
    "Bulk Ceramic": """
    This is about several items of pottery that are described altogether as a group, not as individual pieces. 
    """,
    "Bulk Lithic": """
    This is about several items of stone that are described altogether as a group, not as individual pieces. 
    """,
    "Sample, Collection, or Aggregation": """
    This is about a very general group of one or more physical things collected for study and analysis.
    """,
    "Reference Collection": """
    This is about a group of well-known and described specimens kept to help identify and compare with newly discovered objects.  
    """,
    "stela": """
    This is about a carved or inscribed stone slab or pillar.
    """,
    "Bone grouping": """
    This is about a group or collection of bone found together.
    """,
    "Biological record": """
    This is about the remains of a living thing, including plants, animals, and humans. 
    This record is also about an ecofact.
    """,
    "Lithic": """
    This is about an artifact made of stone.
    """,
    "Radiocarbon Sample": """
    This is about a specimen of organic material used for radiocarbon dating.
    """,
    "Arbitrary Grouping": """
    This is about a chance grouping of database records. 
    """,
    "Sampling site": """
    This is about a place where sample specimens where obtained. A sampling site may or may not be an archaeological site. 
    """,
    "Collection": """
    This is about a set of physical materials, typically artifacts and samples, stored for study. 
    """,
    "Data Publication": """
    This is about a group of related scientific datasets.
    """,
}


TERM_EXPLAINS = [
    """When used with bones, the term "element" generally describes the anatomical name of a type of bone, 
    not a chemical.
    """,
    """Used with pottery, the words "fabric" and "ware" further describe ceramic material."""
]


GENERAL_PASSAGE_STR = """
This is a data record from scientific research.
Creators and contributors authored this data record.
Subjects generally describe the database that contains this record. 
"""

GENERAL_PASSAGE_DATA_PUB_STR = """
This is scientific research project.
Creators and contributors authored this data record.
Subjects generally describe the database that contains this record. 
"""
