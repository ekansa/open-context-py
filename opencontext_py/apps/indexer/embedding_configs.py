
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
    This query retrieves primary location and object records within the database. Locations 
    encompass broad geographic places, regional zones, specific archaeological sites, intra-site 
    sectors, excavation areas, and survey zones. It also identifies structural contexts like 
    features, buildings, excavation units, and stratigraphic layers. Furthermore, this category 
    encompasses individual objects, portable artifacts, analyzed samples, human skeletal remains, 
    and environmental evidence including both faunal and botanical remains. This query 
    allows researchers to isolate specific material components and spatial units of archaeological projects.
    """,
    'media': """
    This query targets diverse forms of digital documentation and primary research media. The 
    retrieved assets include downloadable field photographs, artifact illustrations, documentary 
    videos, interactive 3D models, and comprehensive PDF documents. Additionally, this category 
    encompasses data-rich files such as analytical spreadsheets, geographic information systems data, 
    and other geospatial models. These resources provide visual, spatial, and quantitative 
    verification for archaeological interpretations, allowing researchers to evaluate the raw digital 
    evidence alongside structured descriptive database records.
    """,
    'documents': """
    This query retrieves primary documentation and narrative resources formatted in standard HTML. 
    These textual assets typically comprise original field notes, daily excavation diaries, explicit 
    methodological descriptions, and detailed interpretative commentaries. They represent the qualitative 
    narrative compiled by researchers during fieldwork and analysis. By linking these narrative documents 
    to specific objects or spatial contexts, researchers can reconstruct the thought processes, immediate 
    field observations, and systemic recording strategies that shaped the recovery and interpretation 
    of archaeological evidence.
    """,
}


CLASS_RAG_EXPLAIN_DICT = {
    "Animal Bone": """
    This query targets faunal assemblages, where the term "element" specifically denotes anatomical 
    parts rather than chemical components. Animal bone analysis yields evidence regarding ancient 
    human diet, subsistence strategies, and environmental contexts. Quantifiable patterns in the age and 
    sex distribution of these assemblages clarify past economic practices, including pastoral herding, 
    hunting, milk and cheese production, wool production, and the exploitation of draft animals 
    for labor. Furthermore, faunal remains illuminate household and community food distribution, 
    feasting events, ritual ceremonies, status differentiation, and ideological symbolism.
    """,
    "Human Bone": """
    This query targets human osteological remains, using the term "element" to designate specific anatomical 
    units. Analysis of human skeletal assemblages provides fundamental evidence concerning paleodemographics, 
    population health, physical trauma, pathologies, and dietary profiles. Documented patterns in the age, 
    biological sex, and taphonomy of these bones offer insights into ancient social stratification, economic 
    organization, and gender roles. Additionally, accompanying mortuary treatments and burial practices 
    serve as primary indicators of past religious beliefs, ritual systems, symbolic behaviors, and expressions 
    of social prestige.
    """,
    "Plant remains": """
    This query targets archaeobotanical data, using the terms "family" and "order" to reflect standard biological 
    taxonomy. Plant macro-remains and micro-remains offer evidence regarding ancient human diet, 
    agricultural cultivation, gardening, foraging tactics, and hunter-gatherer subsistence strategies. Botanical assemblages 
    also document specialized domestic activities like textile manufacturing, charcoal production, and fuel 
    selection. Furthermore, specific plant taxa indicate the development of medicine, brewing, fermentation 
    technologies for beer and wine, wild herb exploitation, ritual feasting events, and religious or symbolic 
    practices within past human societies.
    """,
    "Region": """
    This query identifies large-scale spatial contexts and macro-geographic units within the database. 
    Regions encompass modern or historical geopolitical boundaries such as countries, states, and provinces, 
    alongside natural geographic features like seas, river valleys, mountain ranges, and distinct environmental 
    zones. Defining regional parameters allows researchers to aggregate disparate archaeological sites and 
    survey data, facilitating broad spatial analyses, macro-demographic modeling, long-distance trade route 
    reconstruction, and the study of large-scale cultural and environmental adaptations across expansive 
    geographic landscapes.
    """,
    "Object": """
    This query targets individual archaeological artifacts, which represent the portable material culture 
    manufactured, modified, and used by past human populations. While often recovered as broken refuse 
    or discarded garbage, these items encompass tools, weapons, decorative ornaments, architectural fixtures, 
    furniture components, toys, and household utensils. Archaeologists study these objects to 
    understand artistic style, manufacturing processes, raw material sourcing, craft production, 
    specialization, food preparation and consumption, and technological change. 
    Artifacts also inform about trade networks, socio-economic status, households, status, 
    gender dynamics, ritual behaviors, and cultural chronology.
    """,
    "Coin": """
    This query targets specific metallic artifacts utilized primarily as standardized currency. Coins feature 
    distinctive mint marks, inscriptions, and political iconography that establish precise temporal and geographic 
    manufacturing contexts. Beyond providing critical chronological anchors for stratigraphic layers, coins 
    offer detailed insights into state ideologies, art history, regional trade networks, economic practices, 
    and commercial exchange. The presence of coinage typically signifies complex socio-political organizations 
    characterized by centralized state bureaucracies, standardized weights and measures, market economies, and 
    urban settlements.
    """,
    "Pottery": """
    This query targets ceramic artifacts, which represent highly durable components of past material culture. 
    Though occasionally recovered intact within deliberate burial contexts, pottery is routinely found as 
    fragmented sherds (shards) discarded as refuse. Specialized terms like "fabric" and "ware" describe 
    the clay paste matrix and surface treatments. Ceramic analysis provides data regarding food 
    preparation, culinary practices, storage technologies, transport logistics, and trade networks. It also 
    informs research into technical practices, manufacturing styles, pyro-technology, household organization, 
    socio-economic status, and cultural chronology.
    """,
    "Glass": """
    This query focuses on archaeological artifacts manufactured from vitrified materials. Glass objects frequently 
    occur as personal adornments, beads, or specialized containers designed for high-value liquid commodities 
    such as perfumes, oils, and pharmaceuticals. The production of glass reflects complex specialized craftsmanship 
    and sophisticated mastery of high-temperature pyro-technology. Researchers study these artifacts 
    to investigate long-distance trade patterns, economic and manufacturing organization, exchange of technological knowledge, 
    elite socio-economic status, and changing consumer preferences within past societies.
    """,
    "Groundstone": """
    This query targets lithic artifacts modified and shaped through deliberate abrasion, grinding, and polishing 
    techniques. The category encompasses functional domestic tools such as mortars, pestles, manos, and metates, 
    which were vital for processing dietary staples, milling grain, and grinding herbs or spices. Groundstone 
    assemblages also include specialized forms like stone bowls, storage jars, cooking vessels, and ritual incense 
    burners. Additionally, researchers study flat groundstone palettes to document the processing of mineral pigments 
    and powders used in cosmetic applications and symbolic body ornamentation.
    """,
    "Architectural Element": """
    This query identifies structural and decorative components derived from ancient buildings and built environments. 
    Examples include columns, capitals, lintels, roof tiles, and carved molding. Archaeologists analyze these 
    architectural elements to understand construction techniques, raw material procurement, engineering capabilities, 
    and artistic styles. These components provide substantial evidence regarding regional technology, trade networks, 
    and economic systems. Furthermore, their scale and ornamentation inform about socio-economic status, 
    public or private ritual functions, ideological expressions, cultural changes, and architectural chronology.
    """,
    "Non Diagnostic Bone": """
    This query encompasses skeletal remains that lack the morphological landmarks required for precise taxonomic 
    or anatomical identification. Despite their fragmented nature, non-diagnostic bones provide quantitative data 
    regarding overall assemblage size, meat consumption ratios, and intensive bone processing activities. 
    They serve as primary evidence for taphonomic studies, tracking post-depositional modifications 
    such as carnivore gnawing, human trampling, thermal altering, and mechanical weathering. Analyzing these fragments 
    helps researchers evaluate site preservation, site formation processes, and disposal habits within archaeological
    contexts.
    """,
    "Survey Unit": """
    This query identifies bounded regions designated for surface reconnaissance to assess past human landscape use. 
    Survey units are typically documented via systematic field walking, where researchers visually identify and collect 
    surface artifact scatters to detect hidden archaeological sites. Archaeologists may supplement surface observations 
    by digging subsurface test pits or extracting core samples to assess soil stratigraphy and artifact presence. 
    Analyzing spatial distributions across these units reveals long-term regional settlement patterns, demographic shifts, 
    land-use intensity, and human adaptations to changing environments.
    """,
    "Site": """
    This query targets archaeological sites, meaning localized parts of the landscape with evidence for past human 
    occupation and activity. Sites span a wide functional range, encompassing large urban centers, agricultural villages, 
    temporary hunter-gatherer camps, or specialized locales like mines, quarries, military fortresses, regional 
    trading posts, ceremonial and social-gathering locations, and cemeteries. Sites may be identified through remote sensing or 
    pedestrian surveys, known from historical documents and oral histories, or encountered by chance during construction or other
    activities. Sites can undergo detailed documentation through excavation and mapping. They yield data regarding monumental 
    architecture, defensive strategies, social stratification and identity, housing, demographics, spatial organization 
    of economic activites, storage, infrastructure, urban planning, ritual and religious systems, and cultural chronology.
    """,
    "Site Area": """
    This query refers to spatial subdivisions within a larger archaeological site, operating synonymously with terms 
    like "Area", "Operation", or "Field Project". Archaeologists sometimes arbitrarily divide sites into distinct 
    spatial zones to help manage and organize data collection workflows. In other cases, site areas may represent different
    functional contexts such as domestic sectors, public plazas, industrial workshops, defensive perimeters, or elite residential zones. 
    Documenting site areas helps researchers track intra-site socio-economic variations, distinct manufacturing zones, 
    localized depositional histories, architectural sequences, and changing spatial use over time.
    """,
    "Context": """
    This query retrieves records describing specific three-dimensional locations and deposits containing archaeological remains. 
    Attributes of a context often include: spatial coordinates, soil composition, depth, matrix 
    color and density, and exact stratigraphic positioning relative to other layers. Understanding context is fundamental to modern 
    archaeology, as it establishes the precise relational framework between individual artifacts, features, and ecofacts. 
    By analyzing material patterns within contexts, researchers can attempt to reconstruct chronological sequences, 
    behavioral activities, site formation processes, and other patterns reflective of past human societies.
    """,
    "Feature": """
    This query identifies non-portable, human-modified components of an archaeological site. Unlike portable artifacts, 
    features represent fixed structural alterations of space, encompassing walls, prepared floors, storage pits, 
    drainage ditches, hearths, kilns, and domestic refuse heaps. Features provide primary evidence regarding 
    spatial organization, architectural engineering, and localized human activities. By examining the distribution and 
    construction of features, researchers can investigate domestic household behaviors, localized industrial 
    manufacturing, communal defense strategies, socio-economic differentiation, public ritual actions, and site-wide 
    chronological developments.
    """,
    "Structure": """
    This query targets deliberate architectural configurations and complete buildings, which constitute a specific 
    subcategory of non-portable features. Structures provide essential material evidence regarding spatial layouts, 
    construction techniques, raw material selections, and building practices within past societies. Analyzing 
    structural remains allows researchers to interpret household size, domestic spatial organization, socio-economic 
    stratification, public administrative functions, and specialized workshop locations. Furthermore, architectural 
    changes over time document shifting economic conditions, changing domestic organization, political transformations, and 
    occupational sequences across a site.
    """,
    "Space": """
    This query isolates internal divisions, distinct rooms, or specific zones defined within architectural structures. 
    Spaces represent localized archaeological contexts that reveal the spatial logic and functional organization of 
    past buildings. By examining the distinct artifact distributions, specialized features, and soil chemistry within a 
    designated space, researchers can distinguish private domestic quarters from public reception rooms, storage cells, 
    or manufacturing and craft areas. Studying these spatial dynamics provides information about daily household behaviors, gendered 
    activities, socio-economic status, and privacy conventions.
    """,
    "Excavation Unit": """
    This query identifies the distinct, controlled spatial blocks used to record fieldwork data, functioning 
    interchangeably with terms like "Locus", "Lot", or "Unit". An excavation unit
    defines a specific layer, feature, or soil deposit identified by archaeologists during excavation. Researchers document 
    geographic coordinates, elevations, soil matrix properties, and stratigraphic relationships. They group associated materials, 
    including portable artifacts, features, and environmental ecofacts like animal bones or carbonized seeds. 
    Standardizing documentation at the excavation unit level ensures precise spatial control, 
    enabling researchers to reconstruct complex depositional sequences and intra-site contexual patterns.
    """,
    "Locus": """
    This query targets a distinct spatial or stratigraphic unit recorded during field excavations, used interchangeably 
    with terms like "Excavation Unit", "Lot", or "Unit". 
    A locus defines a specific layer, feature, or soil deposit identified by archaeologists during excavation. 
    Researchers document geographic coordinates, elevations, soil matrix properties, and stratigraphic relationships. 
    They group associated materials, including portable artifacts, features, and environmental ecofacts 
    like animal bones or carbonized seeds. Standardizing documentation at the excavation unit level ensures precise 
    spatial control, enabling researchers to reconstruct complex depositional sequences and intra-site contexual patterns.
    """,
    "Lot": """
    This query addresses a designated analytical or spatial unit utilized to aggregate materials during field excavation, 
    sharing its primary definition with "Locus", "Excavation Unit", and "Unit". 
    A "lot" defines a specific layer, feature, or soil deposit identified by archaeologists during excavation. 
    Researchers document geographic coordinates, elevations, soil matrix properties, and stratigraphic relationships. 
    They group associated materials, including portable artifacts, features, and environmental ecofacts 
    like animal bones or carbonized seeds. Standardizing documentation at the excavation unit level ensures precise 
    spatial control, enabling researchers to reconstruct complex depositional sequences and intra-site contexual patterns.
    """,
    "Basket": """
    This query focuses on specific retrieval batches or collection containers used to group material from a defined 
    field context, such as a locus, lot, or excavation unit. Baskets represent the immediate operational level of artifact 
    recovery during active digging. Archaeologists log the context, depth, soil matrix characteristics, and spatial 
    coordinates associated with each basket. Tracking materials at this fine-grained level helps isolate discrete 
    depositional pulses, evaluate artifact density variations, and preserve spatial and other contextual relationships 
    for specialized laboratory analyses.
    """,
    "Area": """
    This query targets macro-spatial divisions within an active archaeological project, operating similarly to terms 
    like "Site Area", "Operation", or "Field Project". Dividing a complex archaeological site into separate areas allows 
    field teams to manage research logistics and compare distinct functional zones. These areas frequently separate specialized 
    sectors, such as domestic housing complexes, areas devoted to manufacturing or craft production, 
    ritual or monumental spaces, or agricultural terraces. Documenting these divisions enables researchers to 
    analyze spatial segregation, intra-site socioeconomic differences, and distinct activities across the landscape.
    """,
    "Trench": """
    This query identifies linear excavation cuts designed to expose stratigraphic profiles across an archaeological site. 
    Trenches provide a long cross-sectional view of complex depositional histories, helping researchers visualize superimposition 
    and site formation processes over time. A single trench often intersects multiple features, structures, and individual 
    depositional layers. Within each trench, specific contexts are further divided into fine-grained units like loci or lots. 
    This spatial framework allows archaeologists to link vertical chronological sequences directly with horizontal spatial configurations.
    """,
    "Square": """
    This query centers on grid-based, geometrically defined units established across an archaeological site to maintain 
    spatial control. Typically arranged within a standardized site grid, squares enable field teams to map features, deposits, 
    artifacts, and ecofacts with greater precision. This geometric framework facilitates accurate recording of horizontal 
    relationships across different excavation areas. By standardizing the horizontal excavation layout into uniform squares, 
    researchers can extrapolate spatial distributions, calculate artifact density metrics, and more easily correlate data 
    across separate field seasons.
    """,
    "Unit": """
    This query designates a fundamental spatial and stratigraphic recording block used during archaeological fieldwork, 
    sharing identical meanings with "Excavation Unit", "Locus", and "Lot". 
    A "unit" defines a specific layer, feature, or soil deposit identified by archaeologists during excavation. 
    Researchers document geographic coordinates, elevations, soil matrix properties, and stratigraphic relationships. 
    They group associated materials, including portable artifacts, features, and environmental ecofacts 
    like animal bones or carbonized seeds. Standardizing documentation at the excavation unit level ensures precise 
    spatial control, enabling researchers to reconstruct complex depositional sequences and intra-site contexual patterns.
    """,
    "Sequence": """
    This query relates to the relative ordering of stratigraphic layers, sharing conceptual ground with terms like 
    "Stratum" and "Phase". Chronological sequences represent a dimension of archaeological context, documenting 
    how separate soil deposits superimpose over time. By analyzing these sequences alongside artifact distributions, researchers 
    establish relative timelines for site activities. Documenting changes in soil characteristics, depth, and spatial coordinates 
    across the sequence allows archaeologists to track cultural developments, shifting economic patterns, and environmental 
    transitions through consecutive depositional phases.
    """,
    "Stratum": """
    This query emphasizes a distinct, homogeneous layer of sedimentary or cultural material isolated within an archaeological 
    sequence, closely related to "Sequence" and "Phase". A stratum represents a specific depositional event or occupational 
    horizon. Archaeologists document each stratum by soil color, composition, depth, artifact and ecofact assemblages, and spatial boundaries. 
    Analyzing artifact assemblages within a secure stratum allows researchers to interpret discrete periods of human activity, 
    evaluate environmental contexts, establish relative chronological frameworks, and compare assemblages of strata across different sites 
    to establish regional chronologies.
    """,
    "Phase": """
    This query describes a high-level chronological period or distinct structural stage identified within an archaeological 
    sequence, operating alongside terms like "Stratum" and "Sequence". A phase aggregates multiple related depositional events 
    and structural styles into a coherent temporal bracket. Archaeologists assign contexts to specific phases based on stylistic 
    shifts in artifacts, architectural modifications, and absolute dates. Documenting these phases enables researchers to synthesize 
    localized site data into broader regional histories, tracking long-term socio-economic changes, political transformations, 
    and cultural transitions.
    """,
    "Mound": """
    This query focuses on elevated, hill-like topographic features resulting from long-term human occupation, architectural 
    collapse, and deliberate landscape modifications. Often referred to as tells or tumuli, mounds represent dense accumulations 
    of stratified cultural debris, overlapping structures, and complex occupational histories. Archaeologists study mounds using 
    surface surveys, remote sensing, and excavation. These landscape features provide extensive evidence regarding persistent 
    settlement choices, long-term demographic trends, monumental building projects, defensive systems, household architecture, 
    and cultural changes over centuries or millennia.
    """,
    "Sample": """
    This query addresses physical specimens systematically collected from fieldwork contexts for specialized laboratory testing 
    and composition analysis. Samples typically comprise small portions of soil, organic material, water, botanical fragments, 
    faunal remains, or artifact residues. Researchers examine these specimens using scientific instruments to determine their 
    elemental, mineralogical, chemical, biochemical, or mechanical properties. The resulting datasets may provide high-resolution 
    information regarding ancient environmental conditions, raw material sourcing, craft manufacturing technologies, dietary habits, 
    and absolute dating evidence for the site.
    """,
    "Bulk Ceramic": """
    This query targets aggregations of pottery sherds that are documented and analyzed collectively as a unified group rather 
    than as individual unique pieces. Bulk ceramic records generally quantify total counts, weights, frequency of vessel shapes and forms, 
    frequency of fabric types within a specific excavation context. This aggregate data provides evidence for statistical modeling, 
    tracking functional differences between contexts, and identifying spatial or chronological differences between pottery assemblages. 
    Additionally, bulk ceramic frequencies are used for mapping site-wide artifact densities and establishing relative chronological trends.
    """,
    "Bulk Lithic": """
    This query encompasses groups of stone tools and manufacturing debris documented collectively as a single aggregate dataset 
    rather than individual specimens. Bulk lithic records typically quantify total counts, aggregate weights, raw material types, 
    and technological categories like flakes, debitage, or cores. Analyzing stone artifacts in bulk allows researchers to 
    reconstruct the full sequence of tool production, evaluate raw material acquisition strategies, identify specialized workshop 
    areas, and map generalized discard behaviors across different spatial contexts.
    """,
    "Sample, Collection, or Aggregation": """
    This query addresses grouped physical specimens and collected materials curated for analytical research, incorporating concepts 
    from samples, formal collections, and material aggregations. These groupings usually represent subsets of soil, environmental 
    ecofacts, or sets of artifacts organized by context, typology, or other characteristics. Researchers examine these assemblages using 
    specialized instrumentation to isolate geochemical, biological, or technological signatures. Curation of these aggregated records 
    better ensures data integrity, providing information resources that subsequent researchers can re-examine for inter-site comparative 
    analysis and regional synthesis.
    """,
    "Reference Collection": """
    This query targets comparative assemblages of fully identified, well-documented specimens maintained to facilitate the 
    classification of newly excavated archaeological materials. Reference collections encompass modern or ancient biological 
    specimens, specialized geological samples, and collections of representative artifacts that illustrate typologies. 
    Typically curated within museums, universities, or specialized research institutions, these collections serve as diagnostic benchmarks. 
    Researchers use them to confirm taxonomic identifications for faunal and botanical remains, verify raw material sources, 
    and standardize stylistic classifications across disparate field projects.
    """,
    "stela": """
    This query focuses on upright, carved, or inscribed stone slabs and pillars that served as public monuments or commemorative 
    markers in antiquity. Archaeologists study stelae to interpret epigraphic texts, learn about artistic styles, and analyze 
    iconographic messaging. These stone monuments provide direct evidence concerning political history, royal lineages, state ideologies, 
    and religious systems. Additionally, their raw material sources reveal ancient trade networks, while their context clarifies public 
    space utilization, social stratification, elite display, gender representation, and historical cultural chronology.
    """,
    "Bone grouping": """
    This query identifies localized concentrations or deliberate clusters of skeletal material found in close physical association 
    during excavation. Bone groupings often indicate specialized depositional processes distinct from generalized domestic refuse 
    disposal. Researchers analyze these spatial clusters to distinguish structured secondary burials, commingled remains, sacrificial 
    offerings, or specialized processing areas. Documenting the spatial configuration and taphonomic history of a bone grouping allows 
    archaeologists to interpret complex mortuary practices, ancient ritual behavior, symbolic expressions, and localized site formation processes.
    """,
    "Biological record": """
    This query addresses the documented presence of organic remains derived from living organisms, encompassing botanical, faunal, 
    and human skeletal data. Also classified as ecofacts, biological records inform researchers about past environmental 
    contexts, ancient ecological conditions, and human-environment interactions. Researchers analyze these organic materials to reconstruct 
    ancient paleoclimates, track regional deforestation, model animal domestication processes, and assess human dietary adaptations. 
    The biological record serves as a primary source for understanding long-term ecological interactions, changing patterns in hunting,
    foraging, herding and agricultural developments.
    """,
    "Lithic": """
    This query targets individual stone artifacts manufactured or modified through intentional knapping, chipping, and flaking 
    processes. Lithic data provides primary evidence regarding ancient technological developments, manufacturing techniques, and 
    raw material procurement strategies. By analyzing tool types and production debris, researchers reconstruct diverse past 
    activities, including hunting, agricultural harvesting, foraging, butchery, and detailed craft carving. Mapping lithic 
    distributions across a site highlights specialized activity zones, distinct household workshops, and localized tool discard 
    habits within past communities.
    """,
    "Radiocarbon Sample": """
    This query identifies specific specimens of preserved organic material, such as charcoal, wood, bone, or seeds, selected for 
    carbon-14 isotopic analysis. Radiocarbon samples provide the foundational data required to calculate absolute calendar dates for 
    many archaeological contexts. By securing absolute dates from these samples, researchers can establish more precise chronological 
    frameworks for occupational phases, structural developments, burial events, and trends in artifact styles. This chronometric 
    data allows archaeologists to cross-date regional sequences and anchor local cultural changes within a definitive historical timeline.
    """,
    "Arbitrary Grouping": """
    This query refers to a non-stratigraphic, database-generated association of records compiled for analytical convenience or 
    procedural organization. Unlike secure archaeological contexts like loci or features, an arbitrary grouping does not reflect past 
    human behavior or natural formation processes. Instead, it serves as a data management tool within this software framework, 
    allowing for browsing and aggregation of large numbers of database records.
    """,
    "Sampling site": """
    This query identifies the explicit geographic location where physical specimens were extracted for scientific analysis. A sampling 
    site can represent a secure context within a recognized archaeological site, or it may encompass off-site environmental locales 
    like lake beds, bogs, and geological outcrops. Documenting the sampling site documents context for interpreting laboratory 
    results, such as palynological sequences or soil geochemistry. This spatial data allows researchers to correlate scientific proxy 
    data accurately with regional environmental histories and localized human activities.
    """,
    "Collection": """
    This query designates an organized assemblage of physical materials, including portable artifacts, environmental ecofacts, and 
    scientific samples, systematically curated for long-term research and preservation. Collections represent the material legacy of 
    field projects, typically managed by research institutions such as museums or university repositories. By maintaining and documenting 
    collections, institutions facilitate curation and access to primary physical evidence. This allows future researchers 
    to re-examine physical objects, apply new analytical technologies, and conduct comparative studies that build upon 
    earlier fieldwork. Collections can also serve important educational and social purposes. They can be displayed in exhibitions, 
    used for teaching, curated in collaboration with community members, and repatriated to facilitate reconciliation and restorative justice.
    """,
    "Data Publication": """
    This query targets integrated sets of related scientific datasets published digitally as primary scholarly contributions. Data 
    publications mirror traditional academic journal articles in peer-review rigor but focus on distributing structured research 
    data rather than narrative synthesis. These assets encompass diverse formats, including granular tabular data, geospatial models, 
    multimedia files, 3D artifact scans, raw outputs from scientific instruments, and digitized field notes. Publishing these datasets 
    provides greater transparency, facilitates open-access research, and allows other researchers to independently query, verify, 
    and reuse primary archaeological data.
    """,
}


EQUIV_OBJ_SLUG_EXPLAIN_DICT = {

    # See: https://en.wikipedia.org/wiki/List_of_domesticated_animals

    # sheep-goat
    "eol-p-32609438-gbif-sub": """
    These small bovid bones reflect uncertain taxonomic identification, because zooarchaeologists 
    have difficulty distinguishing between the bones of sheep and goat. People hunted, herded or kept 
    sheep and goat for: meat, milk, fiber (wool), leather, hides, pelts, horns, vellum, manure, 
    guarding, fighting, racing, weed control, show, pets.
    """,

    # sheep
    "gbif-2441110": """
    Sheep have some morphological differences between wild and domesticated varieties. People hunted, herded 
    or kept sheep for: meat, milk, fiber (especially wool), leather, hides, pelts, horns, vellum, manure, 
    guarding, fighting, racing, weed control, show, pets.
    """,

    # Ovis orientalis 
    "gbif-2441112": """
    Ovis orientalis is the wild ancestor of domestic sheep.
    """,

    # goat
    "gbif-2441056": """
    Goats have some morphological differences between wild and domesticated varieties. People hunted, herded 
    or kept goats for: milk, meat, fiber, skin, horns, vellum, manure, guarding, fighting, racing, weed control, 
    clearing land, show, pets.
    """,

    # Capra aegagrus
    "gbif-4409366": """
    The bezoar goat or wild goat is the wild ancestor domestic goat.
    """,
    
    # pigs
    "gbif-7705930": """
    Pigs have some morphological differences between wild, feral and domesticated varieties. 
    People hunted, herded or kept pigs for: meat, leather, tusks, manure, guarding, fighting, racing, 
    truffle harvesting, weed control, show, pets.
    """,

    # cattle
    "gbif-2441022": """
    Cattle have some morphological differences between the extinct wild and domesticated varieties. 
    People hunted, herded or kept cattle for: meat, milk, leather, hides, fiber, horns, vellum, blood, 
    dung, working, plowing, traction, guarding, fighting, sport, soil fertilization, weed control, 
    worship, show, pets. Cattle herds often had prestige and economic value.
    """,

    # domestic dogs
    "gbif-6164210": """
    Domestic dogs have some morphological and behavioral differences with their wild ancestors. People kept dogs for:
    hunting, herding, guarding, fighting, pets, meat, leather, fiber, racing, working, draft, pack, sport, 
    truffle harvesting, pest control, show.
    """,

    # domestic horse
    "gbif-2440886": """
    People herded or kept horses for: draft, pack, mount, milk, meat, leather, hair, manure, working, plowing, 
    fighting, racing, show, pets. Horses often had prestige, military, and economic value.
    """,

    # domestic donkey
    "gbif-2440891": """
    People herded or kept donkeys for: draft, pack, mount, milk, meat, manure, working, plowing, 
    weed control, show, pets.
    """,

    # Equus
    "gbif-8652950": """
    Equines include a variety of wild species and some economically important domestic species such as horses and 
    donkeys. People herded or kept horses and donkeys for: draft, pack, mount, milk, meat, manure, plowing, pets.
    """,

}