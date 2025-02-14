import duckdb
from django.conf import settings


DUCKDB_PG_OC = 'pg_oc'
DUCKDB_SCHEMA = f'{DUCKDB_PG_OC}.public'

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
    con.execute(f"ATTACH '{pg_conn_str}' AS {DUCKDB_PG_OC} (TYPE POSTGRES);")
    return con

