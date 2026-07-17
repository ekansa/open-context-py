
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
    This is about an artifact made of stone, usually made by chipping and flaking.
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



# Add some additional context information to the strings that get made into
# embeddings. Hopefully this will help make "vibe-searches" more sensible!
ITEM_TYPE_RAG_EXPLAIN_DICT = {
    'subjects': """
    This query finds location and object records. Locations can be geographic places or
    regions. Locations can also be archaeological sites, parts of sites, excavated areas, 
    or areas studied in surveys. This query can also retrieve evidence for features, 
    structures and buildings or other archaeological contexts like excavation units, 
    and stratigraphic layers. This query can also retrieve records of objects, artifacts,
    samples, human remains, and plant and animal remains.
    """,
    'media': """
    This query finds digital media, and may include downloadable images, videos, 3D models,
    PDF documents, spreadsheets, GIS or (geopspatial) data.
    """,
    'documents': """
    This query finds documents in the HTML format. These documents include field notes,
    excavation diaries, descriptions of methods, and other explanatory text resources
    and documentation.
    """,
}


CLASS_RAG_EXPLAIN_DICT = {
    "Animal Bone": """
    This is about animal bones. The word "element" describes anatomy, not a chemical.
    Animal bones provide evidence of food and diet. Patterns in the age and sex of animal bones
    informs about economic practices in herding, hunting, milk production, cheese production,
    wool production, and draft animals and labor. Some animal bones can sometimes indicate 
    pets for companionship or guarding. Some animal bones can indicate feasting, ritual, religion, 
    and symbolism, and prestige.
    """,
    "Human Bone": """
    This is about human bones. The word "element" describes anatomy, not a chemical.
    Human bones provide evidence of demographics, health, injury, food and diet. 
    Patterns in the age and sex of human bones informs about social status, economics,
    and gender. Burial practices can indicate ritual, religion, and symbolism, and prestige.
    """,
    "Plant remains": """
    This is about plant remains. The words "family" and "order" describe biological taxonomy.
    Plant remains provide evidence of food and diet, agriculture, foraging, hunting and gathering. 
    Some plant remains indicate textile production. Some plant remains indicate medicine, brewing,
    fermentation, wine, beer, drug use, herbs and spices, feasting, ritual and religion.
    """,
    "Region": """
    This is about geographic regions. Regions can include countries, states, provinces, cities, seas,
    valleys, or other geographic places.
    """,
    "Object": """
    This is about archaeological artifacts. Artifacts are often broken and discarded as garbage. 
    Artifacts are generally portable material culture and made by people. 
    They can be: tools, weapons, parts of buildings, 
    parts of furniture, toys, utensils, kitchen ware. Artifacts are studied to understand: style, 
    manufacturing techniques, use of raw materials, technology, trade and exchange, economics, 
    social status, gender, households, ritual, religion, burial practices, changes in culture,
    dating and chronology.   
    """,
    "Coin": """
    This is about artifacts, usually made of metal, and likely used as currency. 
    Coins can give precise information about trade, exchange, iconography, economics, and chronology.
    """,
    "Pottery": """
    This is about archaeological artifacts made of ceramic material.
    Pottery is usually broken and fragmented as sherd (shard) and discarded as garbage.  
    Rarely, pottery can be a complete and intact vessel especially if intentionally buried.
    The words "fabric" and "ware" describe ceramic material. Pottery gives evidence about
    cooking, food storage, liquid storage, kitchens, food serving, transportation, trade and economics. 
    Pottery is to understand: style, manufacturing techniques, use of raw materials, technology, trade 
    and exchange, economics, social status, gender, households, ritual, religion, burial practices, 
    changes in culture, dating and chronology. Some pottery can be simple and crude. Some pottery can
    be sophisticated and indicate great skill and expertise with clay, kilns, and pyro-technology. 
    """,
    "Glass": """
    This is about archaeological artifacts made of glass. Glass often used for jewelry and small
    containers of expensive perfumes, drugs, and other liquids. Glass indicates
    great skill and expertise with pyro-technology. Glass can indicate trade, exchange, economics,
    social status and changes in culture.
    """,
    "Groundstone": """
    This is about archaeological artifacts made of rock, that was shaped by grinding and polishing.
    Groundstone can include: mortars, pestles, manos, metates. Ground stone is often used to prepare food,
    especially to grind flour and mix herbs and spices. Sometimes ground stone can include: 
    bowls, jars, and cooking skillets, and incense burners. People used ground stone pallets to make
    powders and pigments for makeup.
    """,
    "Architectural Element": """
    This is about components of buildings, including decorative features. Architectural elements
    are studied to understand: construction, building techniques, style, use of raw materials, 
    technology, trade and exchange, economics, social status, ritual, religion, burial practices, 
    changes in culture, dating and chronology.
    """,
    "Non Diagnostic Bone": """
    This is about bone remains that lack identifying characteristics. Non diagnostic bones mainly inform
    about bulk quantity of bones, bone fragmentation and taphonomy (processes that include trampling,
    gnawing, breaking, and erosion of bone).
    """,
    "Survey Unit": """
    This is about areas of the Earth's surface studied for indications of human activity in the past.
    A survey unit is usually studied by people walking to observe fragments of artifacts on the ground
    that indicate the presence of archaeological sites. Sometimes archaeologists dig test pits or take
    soil samples and core samples to find fragments of artifacts. Patterns observed in the spatial 
    distribution of artifacts can indicate patterns in human settlements and changing environments.
    """,
    "Site": """
    This is about places with indications of human activity in the past. An archaeological site may
    be a large city, a town, a village, or a temporary camp. Some sites may have a special purpose
    like a mine, a quarry, a fortress, a trading post (or caravanserai), a shrine, or a cemetery.
    Archaeological sites are often found in archaeological surveys. Archaeological sites are often
    studied with remote sensing, survey, and excavation. Sites can provide evidence of monuments, 
    defense and warfare, social status, economics, demographics, households, architecture,
    manufacturing, chronology, and culture. 
    """,
    "Site Area": """
    This is about parts of an archaeological site. 
    A site is a place with indications of human activity in the past. Sites can provide evidence of monumental
    architecture, defense and warfare, social status, economics, demographics, households, architecture,
    manufacturing, chronology, and culture. 
    "Site Area", "Area", "Operation", and "Field Project" have similar meanings.
    """,
    "Context": """
    This is about places that contained or contains physical remains studied by archaeologists. 
    Place, the type of soil, depth, coordinates, stratigraphic layer are often aspects of context.
    Archaeologists use context to study patterns in artifacts to understand culture, economics, and chronology.
    """,
    "Feature": """
    This is about archaeologically observed physical modifications of a place, especially an area of ground.
    Remains of architecture, like walls and floors, but also pits, ditches, hearths, ovens, kilns, and dumps can be features.
    Features are examples of material culture that are not portable. Features provide evidence about buildings, architecture, 
    defense and warfare, social status, economics, demographics, households, manufacturing, chronology, and culture. 
    """,
    "Structure": """
    This is about architecture or buildings. These are also archaeological features.
    Structures provide evidence about buildings, architecture, 
    social status, economics, households, manufacturing, chronology, and culture. 
    """,
    "Space": """
    This is zone or parts of architecture or buildings. These are archaeological contexts.
    Spaces provide evidence about buildings, architecture, 
    social status, economics, households, manufacturing, chronology, and culture. 
    """,
    "Excavation Unit": """
    This query is about distinct archaeological contexts recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    Archaeologists record the location, type of soil, depth, coordinates, stratigraphic layer, and presence of features,
    artifacts, ecofacts (like animal bones and plant remains) and density of soil.
    """,
    "Locus": """
    This query is about distinct archaeological contexts recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    Archaeologists record the location, type of soil, depth, coordinates, stratigraphic layer, and presence of features,
    artifacts, ecofacts (like animal bones and plant remains) and density of soil.
    """,
    "Lot": """
    This query is about distinct archaeological contexts recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    Archaeologists record the location, type of soil, depth, coordinates, stratigraphic layer, and presence of features,
    artifacts, ecofacts (like animal bones and plant remains) and density of soil.
    """,
    "Basket": """
    This query is about collections of material from a given archaeological context such as an "Excavation Unit", "Locus", "Lot", or "Unit".
    Archaeologists record the location, type of soil, depth, coordinates, stratigraphic layer, and presence of features,
    artifacts, ecofacts (like animal bones and plant remains) and density of soil.
    """,
    "Area": """
    This query is about parts of an archaeological site. 
    A site is a place with indications of human activity in the past. Sites can provide evidence of monumental
    architecture, defense and warfare, social status, economics, demographics, households, architecture,
    manufacturing, chronology, and culture. 
    "Site Area", "Area", "Operation", and "Field Project" have similar meanings.
    """,
    "Trench": """
    This query is about excavated parts of an archaeological site.
    A site is a place with indications of human activity in the past. Sites can provide evidence of monumental
    architecture, defense and warfare, social status, economics, demographics, households, architecture,
    manufacturing, chronology, and culture.  
    A trench may contain many different excavated contexts, and each context may be called an "Excavation Unit", "Locus", "Lot", or "Unit". 
    """,
    "Square": """
    This query is about geometrically defined parts of an archaeological site. 
    A site is a place with indications of human activity in the past. Sites can provide evidence of monumental
    architecture, defense and warfare, social status, economics, demographics, households, architecture,
    manufacturing, chronology, and culture. 
    A square is used to help archaeologists to help record the locations of features, deposits, contexts, artifacts, etc. 
    """,
    "Unit": """
    This query is about distinct archaeological contexts recorded on a dig.
    Archaeologists record the location, type of soil, depth, coordinates, stratigraphic layer, and presence of features,
    artifacts, ecofacts (like animal bones and plant remains) and density of soil.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Sequence": """
    This query is about stratigraphic layers. Sequences are an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    Place, the type of soil, depth, coordinates, stratigraphic layer are often aspects of context.
    Archaeologists use context to study patterns in artifacts to understand culture, economics, and chronology.
    """,
    "Stratum": """
    This query is about stratigraphic or chronological layers. Strata are an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    Place, the type of soil, depth, coordinates, stratigraphic layer are often aspects of context.
    Archaeologists use context to study patterns in artifacts to understand culture, economics, and chronology.
    """,
    "Phase": """
    This query is about stratigraphic or chronological phases. They are an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    Place, the type of soil, depth, coordinates, stratigraphic layer are often aspects of context.
    Archaeologists use context to study patterns in artifacts to understand culture, economics, and chronology.
    """,
    "Mound": """
    This query is about hill-like parts of archaeological sites.
    A site is a place with indications of human activity in the past. Sites can provide evidence of monumental
    architecture, defense and warfare, social status, economics, demographics, households, architecture,
    manufacturing, chronology, and culture. 
    """,
    "Sample": """
    This query is about very general physical things collected for study and analysis.
    """,
    "Bulk Ceramic": """
    This query is about several items of pottery that are described altogether as a group, not as individual pieces. 
    Bulk ceramic gives general evidence about style, culture, dating and chronology. 
    """,
    "Bulk Lithic": """
    This query is about several items of stone that are described altogether as a group, not as individual pieces.
    Bulk lithic gives general evidence about stone tool production, raw materials, activities, and discard.
    """,
    "Sample, Collection, or Aggregation": """
    This query is about a very general group of one or more physical things collected for study and analysis.
    """,
    "Reference Collection": """
    This query is about groups of well-known and described specimens kept to help identify and compare with newly discovered objects.  
    """,
    "stela": """
    This query is about carved or inscribed stone slabs or pillars.
    Stela are studied to understand: style, 
    manufacturing techniques, use of raw materials, technology, history, iconography, art, economics, 
    social status, gender, ritual, religion, burial practices, changes in culture, warfare, dating and chronology.   
    """,
    "Bone grouping": """
    This query is about groups or collections of bone found together. Groups of bones found together may indicate
    a special deposit such as a burial or sacrifice.
    """,
    "Biological record": """
    This query is about the remains of living things, including plants, animals, and humans. 
    This is also about ecofacts.
    """,
    "Lithic": """
    This is about an artifact made of stone, usually made by chipping and flaking.
    Lithic data provides evidence about stone tool production, raw materials, activities (
    hunting, farming, gathering, food preparation and butchery, carving), activity areas, and discard.
    """,
    "Radiocarbon Sample": """
    This is about specimens of organic material used for radiocarbon dating. Radiocarbon dating
    provides evidence for the age of archaeological sites, deposits, features, burials, artifacts, 
    and ecofacts. 
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
    This is about a group of related scientific datasets. Data publications are akin to academic journal articles,
    but instead of narrative text, they contain analytic data. The data can be: tabular data, geospatial,
    image media files, 3D models, data from scientific instruments, or field notes.
    """,
}