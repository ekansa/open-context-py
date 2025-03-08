import copy
import duckdb
from duckdb.typing import *

from django.conf import settings


from opencontext_py.apps.all_items.isamples import duckdb_con



DB_CON = duckdb_con.create_duck_db_postgres_connection()


ISAMPLES_PQG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pqg (
    pid                     VARCHAR PRIMARY KEY,
    tcreated                INTEGER,
    tmodified               INTEGER,
    otype                   VARCHAR,
    s                       VARCHAR,
    p                       VARCHAR,
    o                       VARCHAR[],
    n                       VARCHAR,
    altids                  VARCHAR[], 
    geometry                BLOB,
    authorized_by           VARCHAR[],
    has_feature_of_interest VARCHAR,
    affiliation             VARCHAR,
    sampling_purpose        VARCHAR,
    complies_with           VARCHAR[],
    project                 VARCHAR,
    alternate_identifiers   VARCHAR[],
    relationship            VARCHAR,
    elevation               VARCHAR,
    sample_identifier       VARCHAR,
    dc_rights               VARCHAR,
    result_time             VARCHAR,
    contact_information     VARCHAR,
    latitude                DOUBLE,
    target                  VARCHAR,
    role                    VARCHAR,
    scheme_uri              VARCHAR,
    is_part_of              VARCHAR[],
    scheme_name             VARCHAR,
    name                    VARCHAR,
    longitude               DOUBLE,
    obfuscated              BOOLEAN,
    curation_location       VARCHAR,
    last_modified_time      VARCHAR,
    access_constraints      VARCHAR[],
    place_name              VARCHAR[],
    description             VARCHAR,
    label                   VARCHAR
);

"""

PID_SAMPSITE = "isam_sampling_site_uri"
PID_GEOLOC_SAMP = "get_deterministic_id(item__geo_source_uri, 'geoloc_')"
PID_GEOLOC_SITE = f"get_deterministic_id({PID_SAMPSITE}, 'geoloc_')"
PID_SAMP = "use_for_pid(persistent_ark, uri)"
PID_SAMPEVENT = "get_deterministic_id(uri, 'sampevent_')"
PID_DIRECT_AGENT = "use_for_pid(direct_sample_dc_orcid, direct_sample_dc_object_uri)"
PID_INDIRECT_AGENT = "use_for_pid(indirect_sample_dc_orcid, indirect_sample_dc_object_uri)"


NEW_KEY_TUPS = {
    duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE: [
        (PID_SAMPSITE, 'PID_SAMPSITE',),
        (PID_GEOLOC_SAMP, 'PID_GEOLOC_SAMP',),
        (PID_GEOLOC_SITE, 'PID_GEOLOC_SITE',),
        (PID_SAMP, 'PID_SAMP',),
        (PID_SAMPEVENT, 'PID_SAMPEVENT',),
    ],
    duckdb_con.ISAMPLES_PREP_PERSON_TABLE: [
        (PID_DIRECT_AGENT, 'PID_DIRECT_AGENT',),
        (PID_INDIRECT_AGENT, 'PID_INDIRECT_AGENT',),
    ]
}

MIN_NUMBER_OBJECT_COUNT_FOR_IDENTIFIED_CONCEPTS = 4


def create_pqg_table(con=DB_CON, schema_sql=ISAMPLES_PQG_SCHEMA_SQL):
    """Create the pqg table"""
    con.execute(schema_sql)


def add_new_keys_to_tables(
    new_key_tups=NEW_KEY_TUPS,
    con=DB_CON
):
    """Add new keys to the iSamples manifest table"""
    for table, key_tups in new_key_tups.items():
        for t_col, col in key_tups:
            sql = f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR DEFAULT NULL"
            con.sql(sql)
            sql = f"UPDATE {table} SET {col} = {t_col}"
            con.sql(sql)


def do_spo_to_pqg_inserts(con=DB_CON):
    """Inserts s, p, o rows from a (temp) spo table into the pqg table"""
    sql = """
    INSERT OR IGNORE INTO  pqg  (
        pid,
        s,
        p,
        o,
        otype
    ) SELECT
        get_deterministic_id(concat(s, p), 'edge_') AS pid,
        s,
        p,
        array_agg(o) AS o,
        otype
        FROM spo
        WHERE s IS NOT NULL
        AND s IN (SELECT pid FROM pqg)
        AND p IS NOT NULL
        AND o IS NOT NULL
        AND o IN (SELECT pid FROM pqg)
        AND get_deterministic_id(concat(s, p), 'edge_') NOT IN
        (SELECT pid FROM pqg)
        GROUP BY s , p, otype
    """
    con.sql(sql)


def make_s_p_o_edge_rows(
    s_col, 
    p_val, 
    o_col, 
    p_col=None, 
    source_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    group_by_cols=None, 
    con=DB_CON
):
    """Add s-p-o edge rows to the pqg table"""

    # First, drop the temporary table if it exists
    sql = "DROP TABLE IF EXISTS spo"
    con.sql(sql)

    if p_col:        
        if not group_by_cols:
            group_by_cols = f"{s_col}, {p_col}, {o_col}"

        sql = f"""
        CREATE TABLE spo AS
        SELECT 
            {s_col} AS s,
            {p_col} AS p,
            {o_col} AS o,
            '_edge_' AS otype
            FROM {source_table}
            WHERE {s_col} IS NOT NULL
            AND {p_col} IS NOT NULL
            AND {o_col} IS NOT NULL
            GROUP BY {group_by_cols}
        """
    else:

        if not group_by_cols:
            group_by_cols = f"{s_col}, {o_col}"
        
        sql = f"""
        CREATE TABLE spo AS
        SELECT 
            {s_col} AS s,
            '{p_val}' AS p,
            {o_col} AS o,
            '_edge_' AS otype
            FROM {source_table}
            WHERE {s_col} IS NOT NULL
            AND {o_col} IS NOT NULL
            GROUP BY {group_by_cols}
        """
    # Now do the SQL to make the temporary table
    con.sql(sql)
    # Use the temporary table to make the insert to the output
    do_spo_to_pqg_inserts(con=con)



def add_direct_geospatial_locations_to_pqg(man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, con=DB_CON):
    """Add geospatial locations to the pqg table.
    These are used directly for the material samples
    """
    sql = f"""
    INSERT OR IGNORE INTO  pqg (
        pid,
        latitude,
        longitude,
        geometry,
        obfuscated,
        elevation,
        otype
    ) SELECT
        PID_GEOLOC_SAMP, 
        ANY_VALUE(item__latitude)::double,
        ANY_VALUE(item__longitude)::double,
        ST_POINT(
            ANY_VALUE(item__longitude), 
            ANY_VALUE(item__latitude)
        ),
        is_obscured(ANY_VALUE(item__geo_specificity)),
        NULL,
        'GeospatialCoordLocation'
        FROM {man_table}
        WHERE item__geo_source_uri  IS NOT NULL
        AND PID_GEOLOC_SAMP NOT IN
        (SELECT pid FROM pqg)
        GROUP BY PID_GEOLOC_SAMP
    """
    con.sql(sql)


def add_sampling_site_geospatial_locations_to_pqg(man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, con=DB_CON):
    """Add sampling site geospatial locations to the pqg table.
    These are used directly for the material samples
    """
    sql = f"""
    INSERT OR IGNORE INTO  pqg (
        pid,
        latitude,
        longitude,
        geometry,
        obfuscated,
        elevation,
        otype
    ) SELECT 
        PID_GEOLOC_SITE, 
        favg(item__latitude)::double,
        favg(item__longitude)::double,
        ST_POINT(
            favg(item__latitude), 
            favg(item__longitude)
        ),
        is_obscured(min(item__geo_specificity)),
        NULL,
        'GeospatialCoordLocation'
        FROM {man_table}
        WHERE isam_sampling_site_uri  IS NOT NULL
        AND PID_GEOLOC_SITE NOT IN
        (SELECT pid FROM pqg)
        GROUP BY PID_GEOLOC_SITE
    """
    con.sql(sql)


def add_sampling_sites_to_pqg(man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, con=DB_CON):
    """Add sampling site geospatial locations to the pqg table.
    These are used directly for the material samples
    """
    sql = f"""
    INSERT OR IGNORE INTO  pqg (
        pid,
        description,
        label,
        place_name,
        is_part_of,
        otype
    ) SELECT 
        PID_SAMPSITE, 
        concat_ws(' ', 'A sampling site documented by: ', ANY_VALUE(project_label)),
        ANY_VALUE(isam_sampling_site_label),
        [ANY_VALUE(path_to___1), ANY_VALUE(path_to___2)],
        NULL,
        'SamplingSite'
        FROM {man_table}
        WHERE isam_sampling_site_uri IS NOT NULL
        AND PID_SAMPSITE NOT IN
        (SELECT pid FROM pqg)
        GROUP BY PID_SAMPSITE
    """
    con.sql(sql)


def add_sampling_events_to_pqg(man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, con=DB_CON):
    """Add sampling events that relate samples to locations, etc. to the pqg table.
    """
    sql = f"""
    INSERT OR IGNORE INTO pqg (
        pid,
        label,
        project,
        otype
    ) SELECT 
        PID_SAMPEVENT,
        concat_ws(' ', 'Sampling event for:', ANY_VALUE(label)),
        ANY_VALUE(project_label),
        'SamplingEvent'
        FROM {man_table}
        WHERE PID_SAMPEVENT NOT IN (SELECT pid FROM pqg)
        GROUP BY PID_SAMPEVENT
    """
    con.sql(sql)


def add_direct_agents_to_pqg(agent_table=duckdb_con.ISAMPLES_PREP_PERSON_TABLE, con=DB_CON):
    """Add sampling events that relate samples to locations, etc. to the pqg table.
    """
    sql = f"""
    INSERT OR IGNORE INTO pqg (
        pid,
        name,
        role,
        otype
    ) SELECT 
        PID_DIRECT_AGENT,
        ANY_VALUE(direct_sample_dc_object_label),
        concat_ws(' ', 'Participated in:', ANY_VALUE(project_label)),
        'Agent'
        FROM {agent_table}
        WHERE PID_DIRECT_AGENT NOT IN (SELECT pid FROM pqg)
        AND direct_sample_dc_object_uri IS NOT NULL
        GROUP BY PID_DIRECT_AGENT
    """
    con.sql(sql)


def add_indirect_agents_to_pqg(agent_table=duckdb_con.ISAMPLES_PREP_PERSON_TABLE, con=DB_CON):
    """Add sampling events that relate samples to locations, etc. to the pqg table.
    """
    sql = f"""
    INSERT OR IGNORE INTO pqg (
        pid,
        name,
        role,
        otype
    ) SELECT 
        PID_INDIRECT_AGENT,
        ANY_VALUE(indirect_sample_dc_object_label),
        concat_ws(' ', 'Participated in:', ANY_VALUE(project_label)),
        'Agent'
        FROM {agent_table}
        WHERE PID_INDIRECT_AGENT NOT IN (SELECT pid FROM pqg)
        AND indirect_sample_dc_object_uri IS NOT NULL
        GROUP BY PID_INDIRECT_AGENT
    """
    con.sql(sql)


def add_material_sample_records_to_pqg(man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, con=DB_CON):
    """Add sampling site geospatial locations to the pqg table.
    These are used directly for the material samples
    """
    sql = f"""
    INSERT OR IGNORE INTO  pqg  (
        pid,
        altids,
        alternate_identifiers,
        complies_with,
        dc_rights,
        description,
        label,
        sample_identifier,
        last_modified_time,
        otype
    ) SELECT 
        PID_SAMP,
        [ANY_VALUE(uri), ANY_VALUE(persistent_ark), ANY_VALUE(persistent_doi)] AS altids_1,
        [ANY_VALUE(uri), ANY_VALUE(persistent_ark), ANY_VALUE(persistent_doi)] AS altids_2,
        NULL,
        NULL,
        concat_ws(
            ' ', 
            'Open Context published',
            concat('"', ANY_VALUE(item_class_label), '"'),
            'sample record from:', 
            path 
        ),
        ANY_VALUE(label),
        ANY_VALUE(label) AS sample_identifier,
        most_recent_to_str(
            ANY_VALUE(revised::TIMESTAMP), 
            ANY_VALUE(updated::TIMESTAMP), 
            ANY_VALUE(indexed::TIMESTAMP), 
            ANY_VALUE(assertion_updated::TIMESTAMP),
            NULL,
            NULL
        )::VARCHAR AS last_modified_time,
        'MaterialSampleRecord'
        FROM {man_table}
        WHERE PID_SAMP NOT IN (SELECT pid FROM pqg)
        AND PID_SAMP IS NOT NULL
        GROUP BY PID_SAMP, PATH
    """
    con.sql(sql)



def add_equiv_identified_concepts_to_pqg(
    assert_table=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE, 
    con=DB_CON,
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    """Add equivalent object identified concepts to the pqg table.
    """
    
    sql = f"""
    INSERT OR IGNORE INTO pqg (
        pid,
        label,
        scheme_name,
        scheme_uri,
        otype
    ) SELECT
        object_equiv_ld_uri, 
        ANY_VALUE(object_equiv_ld_label), 
        ANY_VALUE(con_man.label), 
        concat('https://', ANY_VALUE(con_man.uri)),
        'IdentifiedConcept'
        FROM {assert_table}
        INNER JOIN {db_schema}.oc_all_manifest AS oc_man ON object_equiv_ld_uri = concat('https://', oc_man.uri)
        INNER JOIN {db_schema}.oc_all_manifest AS con_man ON oc_man.context_uuid = con_man.uuid
        WHERE object_equiv_ld_uri IS NOT NULL
        AND object_equiv_ld_uri NOT IN (SELECT pid FROM pqg)
        GROUP BY object_equiv_ld_uri
    """
    con.sql(sql)


def add_object_identified_concepts_to_pqg(
    assert_table=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE, 
    con=DB_CON,
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    """Add project defined object identified concepts to the pqg table.
    """
    sql = f"""
    INSERT OR IGNORE INTO pqg (
        pid,
        label,
        scheme_name,
        scheme_uri,
        description,
        otype
    ) SELECT
        object_uri, 
        concat(ANY_VALUE(predicate_label), ' :: ', ANY_VALUE(object_label)), 
        ANY_VALUE(con_man.label),
        concat('https://', ANY_VALUE(con_man.uri)),
        concat_ws(' ', 'A classification concept used with the attribute', concat('"',  ANY_VALUE(predicate_label),'"'), 'and defined by the project:', ANY_VALUE(con_man.label)),
        'IdentifiedConcept'
        FROM {assert_table}
        INNER JOIN {db_schema}.oc_all_manifest AS oc_man ON object_uri = concat('https://', oc_man.uri)
        INNER JOIN {db_schema}.oc_all_manifest AS con_man ON oc_man.project_uuid = con_man.uuid
        WHERE object_uri IS NOT NULL
        AND object_label IS NOT NULL
        AND oc_man.project_uuid IS NOT NULL
        AND object_item_type = 'types'
        -- Only include identified concepts with a minimum number uses, or where they
        -- have an equivalent linked data URI
        AND (
            obj_count >= {MIN_NUMBER_OBJECT_COUNT_FOR_IDENTIFIED_CONCEPTS}
            OR object_equiv_ld_uri IS NOT NULL
        ) 
        AND object_uri NOT IN (SELECT pid FROM pqg)
        GROUP BY object_uri
    """
    con.sql(sql)


def add_keyword_edges_to_pqg(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    assert_table=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE,
    p_val='keywords',
    o_col='object_equiv_ld_uri',
    where_clause='',
    con=DB_CON,
):
    sql = "DROP TABLE IF EXISTS spo"
    con.sql(sql)
    sql = f"""
        CREATE TABLE spo AS
        SELECT 
            man.PID_SAMP AS s,
            '{p_val}' AS p,
            asserts.{o_col} AS o,
            '_edge_' AS otype
            FROM {assert_table} AS asserts
            INNER JOIN {man_table} AS man ON man.uuid = asserts.subject_uuid
            WHERE man.PID_SAMP IS NOT NULL
            AND asserts.{o_col} IS NOT NULL
            {where_clause}
            GROUP BY man.PID_SAMP, asserts.{o_col}
        """
    # Now do the SQL to make the temporary table
    con.sql(sql)
    # Use the temporary table to make the insert to the output
    do_spo_to_pqg_inserts(con=con)


def add_agent_edges_to_pqg(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    agent_table=duckdb_con.ISAMPLES_PREP_PERSON_TABLE,
    s_col='PID_SAMP',
    p_val='registrant',
    o_col='PID_DIRECT_AGENT',
    group_by_cols='man.PID_SAMP, agents.PID_DIRECT_AGENT',
    con=DB_CON,
):
    sql = "DROP TABLE IF EXISTS spo"
    con.sql(sql)
    sql = f"""
        CREATE TABLE spo AS
        SELECT 
            man.{s_col} AS s,
            '{p_val}' AS p,
            agents.{o_col} AS o,
            '_edge_' AS otype
            FROM {agent_table} AS agents
            INNER JOIN {man_table} AS man ON man.uuid = agents.uuid
            WHERE man.PID_SAMP IS NOT NULL
            AND agents.{o_col} IS NOT NULL
            GROUP BY {group_by_cols}
        """
    # Now do the SQL to make the temporary table
    con.sql(sql)
    # Use the temporary table to make the insert to the output
    do_spo_to_pqg_inserts(con=con)


def add_isamples_entities_to_pqg(con=DB_CON):
    """Add iSamples entities to the pqg table"""
    add_direct_geospatial_locations_to_pqg(con=con)
    add_sampling_site_geospatial_locations_to_pqg(con=con)
    add_sampling_sites_to_pqg(con=con)
    add_sampling_events_to_pqg(con=con)
    add_material_sample_records_to_pqg(con=con)
    add_equiv_identified_concepts_to_pqg(con=con)
    add_object_identified_concepts_to_pqg(con=con)
    add_direct_agents_to_pqg(con=con)
    add_indirect_agents_to_pqg(con=con)


def add_edge_rows_to_pq(con=DB_CON):
    """Add iSamples edge rows that relate entities to the pqg table"""
    # Relate the sampling sites with the sampling sites geolocations
    make_s_p_o_edge_rows(
        s_col='PID_SAMPSITE',
        p_val='site_location',
        p_col=None,
        o_col='PID_GEOLOC_SITE',
        source_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        group_by_cols='PID_SAMPSITE, PID_GEOLOC_SITE',
        con=con,
    )
    # Relate the material samples and the sampling events
    make_s_p_o_edge_rows(
        s_col='PID_SAMP', 
        p_val='produced_by',
        p_col=None,
        o_col='PID_SAMPEVENT',
        source_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        group_by_cols='PID_SAMP, PID_SAMPEVENT',
        con=con,
    )
    # Relate the Sampling events and sampling sites
    make_s_p_o_edge_rows(
        s_col='PID_SAMPEVENT', 
        p_val='sampling_site',
        p_col=None,
        o_col='PID_SAMPSITE',
        source_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        group_by_cols='PID_SAMPEVENT, PID_SAMPSITE',
        con=con,
    )
    # Relate the Sampling events and geolocations for the samples
    make_s_p_o_edge_rows(
        s_col='PID_SAMPEVENT', 
        p_val='sample_location',
        p_col=None,
        o_col='PID_GEOLOC_SAMP',
        source_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        group_by_cols='PID_SAMPEVENT, PID_GEOLOC_SAMP',
        con=con,
    )
    # Relate the material samples and equivalent identified concepts
    add_keyword_edges_to_pqg(
        man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        assert_table=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE,
        p_val='keywords',
        o_col='object_equiv_ld_uri',
        con=con,
    )
    # Relate the material samples and project defined identified concepts
    add_keyword_edges_to_pqg(
        man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        assert_table=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE,
        p_val='keywords',
        o_col='object_uri',
        # Only include identified concepts with a minimum number uses, or where they
        # have an equivalent linked data URI
        where_clause=(
            " AND object_item_type IN ['types', 'uri', 'class'] "
            f"AND (obj_count >= {MIN_NUMBER_OBJECT_COUNT_FOR_IDENTIFIED_CONCEPTS} "
            "OR object_equiv_ld_uri IS NOT NULL) "
        ),
        con=con,
    )
    # Relate the material samples to the direct agents
    add_agent_edges_to_pqg(
        man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        agent_table=duckdb_con.ISAMPLES_PREP_PERSON_TABLE,
        s_col='PID_SAMP',
        p_val='registrant',
        o_col='PID_DIRECT_AGENT',
        group_by_cols='man.PID_SAMP, agents.PID_DIRECT_AGENT',
        con=con,
    )
    # Relate the Sampling events to the indirect agents
    add_agent_edges_to_pqg(
        man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        agent_table=duckdb_con.ISAMPLES_PREP_PERSON_TABLE,
        s_col='PID_SAMPEVENT',
        p_val='responsibility',
        o_col='PID_INDIRECT_AGENT',
        group_by_cols='man.PID_SAMPEVENT, agents.PID_INDIRECT_AGENT',
        con=con,
    )


def summarize_pqg(con=DB_CON):
    """Summarize the pqg table"""
    edge_checks = [
        'site_location',
        'sample_location',
        'sampling_site',
        'produced_by',
        'keywords',
        'registrant',
        'responsibility',
    ]
    for e_check in edge_checks:
        sql = f"SELECT COUNT(pid), '{e_check}' AS predicate FROM pqg WHERE p = '{e_check}'"
        con.sql(sql).show(max_rows=100)
    sql = "SELECT COUNT(pid), otype FROM pqg GROUP BY otype"
    con.sql(sql).show(max_rows=100)
    sql = "SELECT label, description FROM pqg WHERE otype = 'IdentifiedConcept' ORDER BY RANDOM() LIMIT 5; "
    con.sql(sql).show(max_rows=100)