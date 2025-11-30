from django.db import migrations

from opencontext_py.apps.all_items import configs


GEO_OK_ITEM_TYPES = ['subjects', 'projects', 'media', 'tables', 'persons']
GAZETTEER_VOCAB_URIS = ['www.geonames.org', 'pleiades.stoa.org']
DEFAULT_SUBJECTS_ROOTS = configs.DEFAULT_SUBJECTS_ROOTS
MAX_DEPTH = configs.MAX_HIERARCHY_DEPTH


def _to_pg_text_array(values):
    return ", ".join(f"'{val}'" for val in values)


SQL_CREATE_CONTEXT_FUNCTION = f"""
CREATE OR REPLACE FUNCTION oc_manifest_context_chain(target uuid)
RETURNS TABLE (
    item_uuid uuid,
    ancestor_uuid uuid,
    depth integer
)
LANGUAGE SQL
STABLE
AS $function$
WITH RECURSIVE ctx AS (
    SELECT
        m.uuid AS item_uuid,
        m.uuid AS ancestor_uuid,
        0 AS depth,
        CASE
            WHEN m.item_type IN ('media', 'documents') THEN NULL
            ELSE m.context_uuid
        END AS next_context_uuid,
        ARRAY[m.uuid] AS visited
    FROM oc_all_manifest AS m
    LEFT JOIN oc_all_manifest AS ctx_parent ON ctx_parent.uuid = m.context_uuid
    WHERE m.uuid = target
      AND (
          m.item_type = ANY(ARRAY[{_to_pg_text_array(GEO_OK_ITEM_TYPES)}]::text[])
          OR ctx_parent.uri = ANY(ARRAY[{_to_pg_text_array(GAZETTEER_VOCAB_URIS)}]::text[])
      )

    UNION ALL

    SELECT
        ctx.item_uuid,
        parent.uuid AS ancestor_uuid,
        ctx.depth + 1 AS depth,
        CASE
            WHEN parent.uuid::text = ANY(ARRAY[{_to_pg_text_array(DEFAULT_SUBJECTS_ROOTS)}]::text[])
                THEN NULL
            ELSE parent.context_uuid
        END AS next_context_uuid,
        ctx.visited || parent.uuid AS visited
    FROM ctx
    JOIN oc_all_manifest AS parent ON parent.uuid = ctx.next_context_uuid
    WHERE ctx.next_context_uuid IS NOT NULL
      AND parent.item_type = ANY(ARRAY[{_to_pg_text_array(GEO_OK_ITEM_TYPES)}]::text[])
      AND NOT parent.uuid = ANY(ctx.visited)
      AND ctx.depth + 1 <= {MAX_DEPTH}
)
SELECT
    item_uuid,
    ancestor_uuid,
    depth
FROM ctx;
$function$;
"""


SQL_DROP_CONTEXT_FUNCTION = "DROP FUNCTION IF EXISTS oc_manifest_context_chain(uuid);"


SQL_CREATE_BEST_GEO_FUNCTION = """
CREATE OR REPLACE FUNCTION oc_manifest_best_geometry(target uuid)
RETURNS TABLE (
    item_uuid uuid,
    geo_source_uuid uuid,
    geo_spacetime_uuid uuid,
    geo_depth integer,
    geometry_type text,
    geometry jsonb,
    latitude numeric,
    longitude numeric,
    geo_specificity integer
)
LANGUAGE SQL
STABLE
AS $function$
WITH ctx AS (
    SELECT * FROM oc_manifest_context_chain(target)
),
geo_candidates AS (
    SELECT
        ctx.item_uuid,
        ctx.ancestor_uuid AS source_uuid,
        ctx.depth,
        spt.uuid AS spacetime_uuid,
        spt.geometry_type,
        spt.geometry::jsonb AS geometry,
        spt.latitude,
        spt.longitude,
        spt.geo_specificity
    FROM ctx
    JOIN oc_all_spacetime AS spt ON spt.item_uuid = ctx.ancestor_uuid
    WHERE spt.geometry_type IS NOT NULL
),
geo_choice AS (
    SELECT DISTINCT ON (item_uuid)
        item_uuid,
        source_uuid,
        spacetime_uuid,
        depth,
        geometry_type,
        geometry,
        latitude,
        longitude,
        geo_specificity
    FROM geo_candidates
    ORDER BY item_uuid, depth, CASE WHEN source_uuid = item_uuid THEN 0 ELSE 1 END, spacetime_uuid
),
ctx_exists AS (
    SELECT EXISTS (SELECT 1 FROM ctx) AS ok
)
SELECT
    base.item_uuid,
    geo_choice.source_uuid AS geo_source_uuid,
    geo_choice.spacetime_uuid AS geo_spacetime_uuid,
    geo_choice.depth AS geo_depth,
    geo_choice.geometry_type,
    geo_choice.geometry,
    geo_choice.latitude,
    geo_choice.longitude,
    geo_choice.geo_specificity
FROM ctx_exists
JOIN (SELECT target) AS base(item_uuid) ON ctx_exists.ok
LEFT JOIN geo_choice ON geo_choice.item_uuid = base.item_uuid;
$function$;
"""


SQL_DROP_BEST_GEO_FUNCTION = "DROP FUNCTION IF EXISTS oc_manifest_best_geometry(uuid);"


SQL_CREATE_BEST_CHRONO_FUNCTION = """
CREATE OR REPLACE FUNCTION oc_manifest_best_chrono(target uuid)
RETURNS TABLE (
    item_uuid uuid,
    chrono_source_uuid uuid,
    chrono_spacetime_uuid uuid,
    chrono_depth integer,
    earliest numeric,
    start numeric,
    stop numeric,
    latest numeric
)
LANGUAGE SQL
STABLE
AS $function$
WITH ctx AS (
    SELECT * FROM oc_manifest_context_chain(target)
),
chrono_candidates AS (
    SELECT
        ctx.item_uuid,
        ctx.ancestor_uuid AS source_uuid,
        ctx.depth,
        spt.uuid AS spacetime_uuid,
        spt.earliest,
        spt.start,
        spt.stop,
        spt.latest
    FROM ctx
    JOIN oc_all_spacetime AS spt ON spt.item_uuid = ctx.ancestor_uuid
    WHERE spt.earliest IS NOT NULL
      AND spt.latest IS NOT NULL
),
chrono_choice AS (
    SELECT DISTINCT ON (item_uuid)
        item_uuid,
        source_uuid,
        spacetime_uuid,
        depth,
        earliest,
        start,
        stop,
        latest
    FROM chrono_candidates
    ORDER BY item_uuid, depth, CASE WHEN source_uuid = item_uuid THEN 0 ELSE 1 END, spacetime_uuid
),
ctx_exists AS (
    SELECT EXISTS (SELECT 1 FROM ctx) AS ok
)
SELECT
    base.item_uuid,
    chrono_choice.source_uuid AS chrono_source_uuid,
    chrono_choice.spacetime_uuid AS chrono_spacetime_uuid,
    chrono_choice.depth AS chrono_depth,
    chrono_choice.earliest,
    chrono_choice.start,
    chrono_choice.stop,
    chrono_choice.latest
FROM ctx_exists
JOIN (SELECT target) AS base(item_uuid) ON ctx_exists.ok
LEFT JOIN chrono_choice ON chrono_choice.item_uuid = base.item_uuid;
$function$;
"""


SQL_DROP_BEST_CHRONO_FUNCTION = "DROP FUNCTION IF EXISTS oc_manifest_best_chrono(uuid);"


SQL_CREATE_VIEW = """
CREATE OR REPLACE VIEW oc_all_manifest_best_spacetime AS
SELECT
    man.uuid AS item_uuid,
    geo.geo_source_uuid,
    geo.geo_spacetime_uuid,
    geo.geo_depth,
    geo.geometry_type,
    geo.geometry,
    geo.latitude,
    geo.longitude,
    geo.geo_specificity,
    chrono.chrono_source_uuid,
    chrono.chrono_spacetime_uuid,
    chrono.chrono_depth,
    chrono.earliest,
    chrono.start,
    chrono.stop,
    chrono.latest
FROM oc_all_manifest AS man
LEFT JOIN LATERAL oc_manifest_best_geometry(man.uuid) AS geo ON TRUE
LEFT JOIN LATERAL oc_manifest_best_chrono(man.uuid) AS chrono ON TRUE;
"""


SQL_DROP_VIEW = "DROP VIEW IF EXISTS oc_all_manifest_best_spacetime;"


SQL_CREATE_MATERIALIZED_VIEW = """
CREATE MATERIALIZED VIEW oc_all_manifest_cached_spacetime AS

SELECT DISTINCT ON (spt.item_uuid)
    spt.item_uuid AS item_uuid,
    spt.geo_source_uuid,
    spt.geo_spacetime_uuid,
    spt.geo_depth,
    spt.geometry_type,
    spt.geometry,
    spt.latitude,
    spt.longitude,
    spt.geo_specificity,
    spt.chrono_source_uuid,
    spt.chrono_spacetime_uuid,
    spt.chrono_depth,
    spt.earliest,
    spt.start,
    spt.stop,
    spt.latest,
    'direct' AS reference_type
FROM oc_all_manifest_best_spacetime AS spt
WHERE (
    spt.geo_source_uuid IS NOT NULL
    OR
    spt.chrono_source_uuid IS NOT NULL
)
ORDER BY 
    spt.item_uuid, 
    spt.geo_source_uuid DESC NULLS LAST, 
    spt.chrono_source_uuid DESC NULLS LAST

UNION

SELECT DISTINCT ON (spt.item_uuid)
    spt.item_uuid AS item_uuid,
    spt.geo_source_uuid,
    spt.geo_spacetime_uuid,
    spt.geo_depth,
    spt.geometry_type,
    spt.geometry,
    spt.latitude,
    spt.longitude,
    spt.geo_specificity,
    spt.chrono_source_uuid,
    spt.chrono_spacetime_uuid,
    spt.chrono_depth,
    spt.earliest,
    spt.start,
    spt.stop,
    spt.latest,
    'indirect' AS reference_type
FROM oc_all_manifest AS man
JOIN oc_all_manifest_best_spacetime AS spt_null ON (
    man.uuid = spt_null.item_uuid
)
JOIN LATERAL (
    SELECT ass.object_uuid
    FROM oc_all_assertions AS ass
    JOIN oc_all_manifest AS obj_man ON (
        ass.object_uuid = obj_man.uuid
    )
    WHERE man.uuid = ass.subject_uuid
    AND
    obj_man.item_type = 'subjects'
    ORDER BY ass.obs_sort, ass.sort, obj_man.sort
    LIMIT 1
) ass ON TRUE
JOIN oc_all_manifest_best_spacetime AS spt ON (
    ass.object_uuid = spt.item_uuid
)
WHERE man.item_type IN ('media', 'documents', 'tables', 'projects')
AND 
(
    spt_null.geo_source_uuid IS NULL
    AND
    spt_null.chrono_source_uuid IS NULL
)
AND 
(
    spt.geo_source_uuid IS NOT NULL
    OR
    spt.chrono_source_uuid IS NOT NULL
)
ORDER BY 
    spt.item_uuid, 
    spt.geo_source_uuid DESC NULLS LAST, 
    spt.chrono_source_uuid DESC NULLS LAST
;


CREATE INDEX oc_all_manifest_cached_spacetime_item
  ON oc_all_manifest_cached_spacetime (item_uuid);

CREATE INDEX oc_all_manifest_cached_spacetime_geo_source_spt
  ON oc_all_manifest_cached_spacetime (geo_spacetime_uuid);

CREATE INDEX oc_all_manifest_cached_spacetime_chrono_source_spt
  ON oc_all_manifest_cached_spacetime (chrono_spacetime_uuid);

"""

SQL_DROP_MATERIALIZED_VIEW = "DROP MATERIALIZED VIEW IF EXISTS oc_all_manifest_cached_spacetime;"


class Migration(migrations.Migration):

    dependencies = [
        ('all_items', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(SQL_CREATE_CONTEXT_FUNCTION, SQL_DROP_CONTEXT_FUNCTION),
        # migrations.RunSQL(SQL_CREATE_BEST_GEO_FUNCTION, SQL_DROP_BEST_GEO_FUNCTION),
        # migrations.RunSQL(SQL_CREATE_BEST_CHRONO_FUNCTION, SQL_DROP_BEST_CHRONO_FUNCTION),
        # migrations.RunSQL(SQL_CREATE_VIEW, SQL_DROP_VIEW),
        # migrations.RunSQL(SQL_CREATE_MATERIALIZED_VIEW, SQL_DROP_MATERIALIZED_VIEW ),
    ]

