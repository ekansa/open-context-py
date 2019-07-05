import pytest
from django.conf import settings


def _check_db_postgres():
    default_db = settings.DATABASES.get("default")
    if default_db is None:
        return False
    engine = default_db.get("ENGINE")
    if engine is None:
        return False
    return "postgresql" in engine


needs_postgres = pytest.mark.skipif(
    not _check_db_postgres(),
    reason="Requires running against PostgreSQL",
)
