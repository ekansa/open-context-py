
import datetime
import hashlib
import json
import uuid as GenUUID



import duckdb
from duckdb.typing import *

from django.conf import settings


from opencontext_py.apps.all_items.isamples import duckdb_con


DB_CON = duckdb_con.create_duck_db_postgres_connection()



def get_path_level_item(path: str, level: int) -> str:
    if not path:
        return None
    path_list = path.split('/')
    if level >= len(path_list):
        return None
    return path_list[level]


def get_path_upto_level(path: str, level: int) -> str:
    if not path:
        return None
    path_list = path.split('/')
    level += 1
    if level > len(path_list):
        return None
    return '/'.join(path_list[:level])


def get_deterministic_id(values: str, prefix='') -> str:
    values = str(values)
    hash_obj = hashlib.sha1()
    hash_obj.update(values.encode('utf-8'))
    hash_id =  hash_obj.hexdigest()
    return f'{prefix}{hash_id}'


def is_obscured(geo_spec:int) -> bool:
    if geo_spec is None:
        return False
    if geo_spec < 0:
        return True
    return False


def use_for_pid(best_id: str, fallback_id:str) -> str:
    best_id = str(best_id)
    if not best_id or best_id == 'None':
        return fallback_id
    return best_id


def make_alt_id_list(id_1:str='', id_2:str='', id_3:str='', id_4:str='') -> list:
    id_list = [id for id in [id_1, id_2, id_3, id_4] if id is not None and id != '']
    return id_list


def most_recent_to_str(
    val1:datetime.datetime=None,
    val2:datetime.datetime=None,
    val3:datetime.datetime=None,
    val4:datetime.datetime=None,
    val5:datetime.datetime=None,
    val6:datetime.datetime=None,
) -> str:
    datetimes = [dt for dt in [val1, val2, val3, val4, val5, val6] if dt is not None]
    if len(datetimes) < 1:
        # We weirdly have no timestamps, so
        # return the current time.
        return datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
    recent = max(datetimes)
    return recent.strftime('%Y-%m-%dT%H:%M:%SZ')


def define_duckdb_functions(con=DB_CON):
    con.create_function(
        "get_path_level_item", 
        get_path_level_item, 
        [VARCHAR, BIGINT], VARCHAR, 
        null_handling="special"
    )
    con.create_function(
        "get_path_upto_level", 
        get_path_upto_level, 
        [VARCHAR, BIGINT], VARCHAR, 
        null_handling="special"
    )
    con.create_function(
        "get_deterministic_id", 
        get_deterministic_id, 
        [VARCHAR, VARCHAR], VARCHAR, 
        null_handling="special"
    )
    con.create_function(
        "is_obscured", 
        is_obscured, 
        [BIGINT], BOOLEAN, 
        null_handling="special"
    )
    con.create_function(
        "use_for_pid", 
        use_for_pid, 
        [VARCHAR, VARCHAR], VARCHAR, 
        null_handling="special"
    )
    con.create_function(
        "make_alt_id_list", 
        make_alt_id_list, 
        [VARCHAR, VARCHAR, VARCHAR, VARCHAR], 'VARCHAR[]', 
        null_handling="special"
    )
    con.create_function(
        "most_recent_to_str", 
        most_recent_to_str, 
        [TIMESTAMP] * 6, VARCHAR, 
        null_handling="special"
    )