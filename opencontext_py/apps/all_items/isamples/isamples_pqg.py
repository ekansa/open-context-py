import copy
import duckdb
from duckdb.typing import *

from django.conf import settings

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.isamples import duckdb_con
from opencontext_py.apps.all_items.isamples import vocab_mappings
from opencontext_py.apps.all_items.isamples import utilities as duck_utils


DB_CON = duckdb_con.create_duck_db_postgres_connection()

ISAMPLES_ROW_ID_SEQUENCE_SQL = 'CREATE SEQUENCE row_id_sequence START 1;'

ISAMPLES_PQG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pqg (
    row_id                  INTEGER PRIMARY KEY DEFAULT nextval('row_id_sequence'),
    pid                     VARCHAR UNIQUE NOT NULL,
    tcreated                INTEGER,
    tmodified               INTEGER,
    otype                   VARCHAR,
    s                       INTEGER,
    p                       VARCHAR,
    o                       INTEGER[],
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
    label                   VARCHAR,
    thumbnail_url           VARCHAR
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

# Mimimum number of uses Open Context "types" to be included 
# as iSamples identified concepts
MIN_NUMBER_OBJECT_COUNT_FOR_IDENTIFIED_CONCEPTS = 4




def create_pqg_table(con=DB_CON, sequence_sql=ISAMPLES_ROW_ID_SEQUENCE_SQL, schema_sql=ISAMPLES_PQG_SCHEMA_SQL):
    """Create the pqg table"""
    con.execute(sequence_sql)
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


def add_preliminary_material_types_to_man_table(
    vocab_concepts_dict=vocab_mappings.MAP_ITEM_CLASS_LABEL_MATERIAL_TYPES,
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    con=DB_CON,
):
    """Updates the isam_manifest table with preliminary material types, as
    configured for different item_class_labels. This is considered a
    default material type, which can be updated later with more specific
    information from assertions.
    """
    for item_class_label, type_dict in vocab_concepts_dict.items():
        mtype_pid = type_dict['pid']
        sql = f"""
        UPDATE {man_table}
        SET isam_msamp_material_type = '{mtype_pid}'
        WHERE item_class_label = '{item_class_label}'
        """
        con.sql(sql)
    sql = f"""
    SELECT item_class_label, isam_msamp_material_type, COUNT(uuid) AS count
    FROM {man_table}
    GROUP BY item_class_label, isam_msamp_material_type
    ORDER BY count DESC
    """
    print('Preliminary material types in the manifest table:')
    con.sql(sql).show(max_rows=100)


def update_material_types_in_man_tab_via_assertions(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    assert_table=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE, 
    con=DB_CON,
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    """Update the material types in the manifest table via assertions. We need to use
    'Consists of' assertions to get the material types by association from controlled
    vocabulary concepts that have 'interoperability mappings' to iSamples material types.
    """
    pred_interop_uuid = duck_utils.cast_duckdb_uuid(configs.PREDICATE_OC_INTEROP_MAP_UUID)
    
    sql = f"""
    UPDATE {man_table}
    SET isam_msamp_material_type = concat('https://', oc_isam_man.uri)
    FROM {assert_table} AS asserts
    INNER JOIN {db_schema}.oc_all_manifest AS oc_man ON asserts.object_equiv_ld_uri = concat('https://', oc_man.uri)
    INNER JOIN {db_schema}.oc_all_assertions AS oc_a ON oc_man.uuid = oc_a.subject_uuid
    INNER JOIN {db_schema}.oc_all_manifest AS oc_isam_man ON oc_a.object_uuid = oc_isam_man.uuid
    WHERE asserts.subject_uuid = {man_table}.uuid
    AND asserts.predicate_equiv_ld_label = 'Consists of'
    AND oc_a.predicate_uuid = {pred_interop_uuid}
    """
    con.sql(sql)
    sql = f"""
    SELECT item_class_label, isam_msamp_material_type, COUNT(uuid) AS count
    FROM {man_table}
    GROUP BY item_class_label, isam_msamp_material_type
    ORDER BY count DESC
    """
    print('Final material types in the manifest table:')
    con.sql(sql).show(max_rows=100)


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
        get_deterministic_id(concat(spo.s_pid, spo.p), 'edge_') AS pid,
        s_pqg.row_id AS s,
        spo.p,
        array_agg(o_pqg.row_id) AS o,
        spo.otype
        FROM spo
        INNER JOIN pqg AS s_pqg ON spo.s_pid = s_pqg.pid
        INNER JOIN pqg AS o_pqg ON spo.o_pid = o_pqg.pid
        WHERE spo.s_pid IS NOT NULL
        AND spo.p IS NOT NULL
        AND spo.o_pid IS NOT NULL
        AND get_deterministic_id(concat(spo.s_pid, spo.p), 'edge_') NOT IN
        (SELECT pid FROM pqg)
        GROUP BY s_pid, s_pqg.row_id, spo.p, spo.otype, 
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
            {s_col} AS s_pid,
            {p_col} AS p,
            {o_col} AS o_pid,
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
            {s_col} AS s_pid,
            '{p_val}' AS p,
            {o_col} AS o_pid,
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
        thumbnail_url,
        otype
    ) SELECT 
        PID_SAMP,
        make_alt_id_list(ANY_VALUE(uri), ANY_VALUE(persistent_ark), ANY_VALUE(persistent_doi), NULL) AS altids_1,
        make_alt_id_list(ANY_VALUE(uri), ANY_VALUE(persistent_ark), ANY_VALUE(persistent_doi), NULL) AS altids_2,
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
        ANY_VALUE(object_thumbnail) AS thumbnail_url,
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


def add_vocab_concepts_to_pqg(vocab_concepts_dict, con=DB_CON):
    for _, type_dict in vocab_concepts_dict.items():
        if not type_dict.get('label'):
            continue
        print(f'Adding {type_dict["label"]} to pqg')
        sql = f"""
        INSERT OR IGNORE INTO pqg (
            pid,
            label,
            scheme_name,
            scheme_uri,
            description,
            otype
        ) VALUES (
            '{type_dict['pid']}', 
            '{type_dict['label']}',
            '{type_dict['scheme_name']}',
            '{type_dict['scheme_uri']}',
            '{type_dict['description']}',
            '{type_dict['otype']}'
        )
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
            man.PID_SAMP AS s_pid,
            '{p_val}' AS p,
            asserts.{o_col} AS o_pid,
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
            man.{s_col} AS s_pid,
            '{p_val}' AS p,
            agents.{o_col} AS o_pid,
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


def add_material_sample_object_type_edges_to_pqg(
    vocab_concepts_dict=vocab_mappings.MAP_ITEM_CLASS_LABEL_MATERIAL_SAMPLE_OBJECT_TYPES,
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    p_val='has_sample_object_type',
    con=DB_CON,
):
    for item_class_label, type_dict in vocab_concepts_dict.items():
        object_pid = type_dict['pid']
        # First do the SQL for the material sample record.
        sql = "DROP TABLE IF EXISTS spo"
        con.sql(sql)
        sql = f"""
            CREATE TABLE spo AS
            SELECT 
                man.PID_SAMP AS s_pid,
                '{p_val}' AS p,
                '{object_pid}' AS o_pid,
                '_edge_' AS otype
                FROM {man_table} AS man
                WHERE man.PID_SAMP IS NOT NULL
                AND man.item_class_label = '{item_class_label}'
                GROUP BY man.PID_SAMP
            """
        # Now do the SQL to make the temporary table
        con.sql(sql)
        # Use the temporary table to make the insert to the output
        do_spo_to_pqg_inserts(con=con)


def add_material_type_edges_to_pqg(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    p_val='has_material_category',
    con=DB_CON,
):
    """Add material type edges to the pqg table from data in the
    isam_msamp_material_type column of the iSamples manifest table.
    """
    sql = "DROP TABLE IF EXISTS spo"
    con.sql(sql)
    sql = f"""
        CREATE TABLE spo AS
        SELECT 
            man.PID_SAMP AS s_pid,
            '{p_val}' AS p,
            man.isam_msamp_material_type AS o_pid,
            '_edge_' AS otype
            FROM {man_table} AS man
            WHERE man.PID_SAMP IS NOT NULL
            AND man.isam_msamp_material_type IS NOT NULL
            GROUP BY man.PID_SAMP, man.isam_msamp_material_type
        """
    # Now do the SQL to make the temporary table
    con.sql(sql)
    # Use the temporary table to make the insert to the output
    do_spo_to_pqg_inserts(con=con)


def add_sampling_site_edges_to_pqg(
    vocab_concepts_dict=vocab_mappings.MAP_SITE_TYPE_SAMPLED_SITE_TYPES,
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    p_val='has_context_category',
    con=DB_CON,
):
    for site_type, type_dict in vocab_concepts_dict.items():
        object_pid = type_dict['pid']
        # First do the SQL for the sample event.
        if False:
            # Skip this, since it seems redundant.
            sql = "DROP TABLE IF EXISTS spo"
            con.sql(sql)
            sql = f"""
                CREATE TABLE spo AS
                SELECT 
                    man.PID_SAMPEVENT AS s_pid,
                    '{p_val}' AS p,
                    '{object_pid}' AS o_pid,
                    '_edge_' AS otype
                    FROM {man_table} AS man
                    WHERE man.PID_SAMPEVENT IS NOT NULL
                    AND man.isam_sampling_site_type = '{site_type}'
                    GROUP BY man.PID_SAMPEVENT
                """
            # Now do the SQL to make the temporary table
            con.sql(sql)
            do_spo_to_pqg_inserts(con=con)
        # Now do the SQL for the MaterialSampleRecord
        sql = "DROP TABLE IF EXISTS spo"
        con.sql(sql)
        sql = f"""
            CREATE TABLE spo AS
            SELECT 
                man.PID_SAMP AS s_pid,
                '{p_val}' AS p,
                '{object_pid}' AS o_pid,
                '_edge_' AS otype
                FROM {man_table} AS man
                WHERE man.PID_SAMP IS NOT NULL
                AND man.isam_sampling_site_type = '{site_type}'
                GROUP BY man.PID_SAMP
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
    add_vocab_concepts_to_pqg(
        vocab_concepts_dict=vocab_mappings.MAP_ITEM_CLASS_LABEL_MATERIAL_SAMPLE_OBJECT_TYPES, 
        con=con,
    )
    add_vocab_concepts_to_pqg(
        vocab_concepts_dict=vocab_mappings.MAP_ITEM_CLASS_LABEL_MATERIAL_TYPES, 
        con=con,
    )
    add_vocab_concepts_to_pqg(
        vocab_concepts_dict=vocab_mappings.MAP_SITE_TYPE_SAMPLED_SITE_TYPES, 
        con=con,
    )



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
    # Relate the Material Sample Records to the object types
    add_material_sample_object_type_edges_to_pqg(
        vocab_concepts_dict=vocab_mappings.MAP_ITEM_CLASS_LABEL_MATERIAL_SAMPLE_OBJECT_TYPES,
        man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        p_val='has_sample_object_type',
        con=con,
    )
    # Add the edges for the material types
    add_material_type_edges_to_pqg(
        man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        p_val='has_material_category',
        con=con,
    )
    # Relate the Sampling sites to the sampling site types
    add_sampling_site_edges_to_pqg(
        vocab_concepts_dict=vocab_mappings.MAP_SITE_TYPE_SAMPLED_SITE_TYPES,
        man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
        p_val='has_context_category',
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
        'has_sample_object_type',
        'has_material_category',
        'has_context_category',
    ]
    for e_check in edge_checks:
        sql = f"SELECT COUNT(pid), '{e_check}' AS predicate FROM pqg WHERE p = '{e_check}'"
        con.sql(sql).show(max_rows=100)
    sql = "SELECT COUNT(pid), otype FROM pqg GROUP BY otype"
    con.sql(sql).show(max_rows=100)
    sql = "SELECT label, description FROM pqg WHERE otype = 'IdentifiedConcept' ORDER BY RANDOM() LIMIT 5; "
    con.sql(sql).show(max_rows=100)
    sql = """
    SELECT pqg.label,
    pqg.description,
    opqg.label
    FROM pqg
    INNER JOIN pqg AS ppqg ON (
        pqg.row_id = ppqg.s
        AND ppqg.p = 'has_context_category'
    )
    INNER JOIN pqg AS opqg ON opqg.row_id = list_any_value(ppqg.o)
    WHERE pqg.otype = 'MaterialSampleRecord'
    ORDER BY RANDOM()
    LIMIT 10
    """
    con.sql(sql).show(max_rows=10)