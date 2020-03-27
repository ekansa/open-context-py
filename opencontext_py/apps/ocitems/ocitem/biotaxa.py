
# Biological Taxonomy Requirements. This dict
# configures how two different 
PREDICATES_BIO_TAXONOMIES = {
    # NOTE: eol URIs and this predicate URI 
    # are to be deprecated.
    'http://purl.org/NET/biol/ns#term_hasTaxonomy': {
        'includes': ['eol.org'],
        'excludes': ['#gbif-sub'],
    },
    # NOTE: this predicate URI and GBIF uris
    # are preferred. However, 'sheep/goat' will remain
    # a EOL uri, but with a #gbif-sub suffix to it.
    'http://purl.obolibrary.org/obo/FOODON_00001303': {
        'includes': ['gbif.org', '#gbif-sub'],
        'excludes': [],
    },
}

def biological_taxonomy_validation(
    act_pred, 
    object_uri, 
    predicates_bio_taxonomies=PREDICATES_BIO_TAXONOMIES
):
    """For biological taxa linked data, checks if an object_uri
    is OK for a predicate
    """
    # NOTE: This is needed because we're deprecating EOL
    # URIs in favor of GBIF, but want to maintain 
    # backward compatibility
    if not act_pred in predicates_bio_taxonomies:
        # Not a predicate for biological taxa, default
        # to valid
        return True
    check_dict = predicates_bio_taxonomies[act_pred]
    for exclude in check_dict['excludes']:
        if exclude in object_uri:
            return False
    for include in check_dict['includes']:
        if include in object_uri:
            return True
    return False