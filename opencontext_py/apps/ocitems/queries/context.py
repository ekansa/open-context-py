from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.queries.security import SecurityForQuery
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest


class ContextQueries():
    """
    This includes queries that use PostgresSQL functions to improve performance
    It represents a bit of a security risk for SQL injection attacks.
    So these methods should not be used unless a passed UUID parameter
    is already known to be safe through use in Django's normal querying model

from opencontext_py.apps.ocitems.queries.context import ContextQueries
contqs = ContextQueries()
contqs.get_contain_parents_list('3C33A62A-0A21-4C1B-B285-B9BB5AC83053')

    """
    def __init__(self):
        self.seems_safe = False

    def write_recursive_parent_procedure(self):
        """ writes PostgresSQL stored procedures
            to recursively lookup parent items
        """
        proc = (
            'CREATE OR REPLACE FUNCTION '
            'find_contain_parent(child_uuid character varying) '
            'RETURNS character varying AS $$ '
            'DECLARE '
            'parent_uuid character varying; '
            'BEGIN '
            'SELECT INTO parent_uuid as_p.uuid '
            'FROM oc_assertions AS as_p '
            'WHERE as_p.object_uuid = child_uuid '
            'AND as_p.predicate_uuid = \'oc-gen:contains\' '
            'AND as_p.visibility = 1; '
            'RETURN parent_uuid; '
            'END; '
            '$$ LANGUAGE plpgsql; '
            ' '
            'CREATE OR REPLACE FUNCTION '
            'get_parents(child_uuid character varying) '
            'RETURNS TABLE (rank int, '
            'parent_uuid character varying) AS $$ '
            'BEGIN '
            'rank = 0; '
            'parent_uuid = child_uuid; '
            'WHILE parent_uuid IS NOT NULL LOOP '
            'rank := rank + 1; '
            'parent_uuid := find_contain_parent(parent_uuid); '
            'IF parent_uuid IS NOT NULL THEN '                
            'RETURN NEXT; '
            'END IF; '
            'END LOOP; '
            'RETURN; '
            'END; '
            '$$ LANGUAGE plpgsql; ')
        return proc

    def get_contain_parents_list(self, uuid):
        """ gets a list of parent items """
        output = False
        sfq = SecurityForQuery()
        uuid = sfq.check_uuid_saftey(uuid)
        if uuid is not False:
            proc = self.write_recursive_parent_procedure()
            query = ('SELECT par.rank AS rank, m.uuid AS uuid, m.label AS label, '
                     'm.slug AS slug, m.class_uri AS class_uri '
                     'FROM get_parents(%s) AS par '
                     'JOIN oc_manifest AS m ON par.parent_uuid = m.uuid; ')
            cursor = connection.cursor()
            cursor.execute(proc + query, [uuid])
            rows = self.dictfetchall(cursor)
            output = rows
        return output

    def dictfetchall(self, cursor):
        """ Return all rows from a cursor as a dict """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
