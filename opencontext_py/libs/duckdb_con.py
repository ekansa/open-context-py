import duckdb
from duckdb.typing import *

from django.conf import settings


DUCKDB_PG_OC = 'pg_oc'
DUCKDB_SCHEMA = f'{DUCKDB_PG_OC}.public'

ISAMPLES_PREP_MANIFEST_TABLE = 'isam_man'
ISAMPLES_PREP_ASSERTION_TABLE = 'isam_asserts'
ISAMPLES_PREP_PERSON_TABLE = 'isam_persons'


def create_duck_db_postgres_connection(pg_connection_name=DUCKDB_PG_OC):
    """Create a DuckDB connection to a PostgreSQL database"""
    pg_settings = settings.DATABASES['default']

    pg_conn_str = (
        f"postgresql://{pg_settings['USER']}:{pg_settings['PASSWORD']}"
        f"@{pg_settings['HOST']}:{pg_settings['PORT']}/{pg_settings['NAME']}"
    )
    con = duckdb.connect(":memory:")
    con.execute("INSTALL postgres;")
    con.execute("LOAD postgres;")
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.execute(f"ATTACH '{pg_conn_str}' AS {DUCKDB_PG_OC} (TYPE POSTGRES);")
    return con



def cast_duckdb_uuid(uuid):
    """Convert a uuid to a DuckDB compatible UUID string"""
    return f"CAST('{str(uuid)}' AS UUID)"

