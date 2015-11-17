import re
from django.conf import settings


class SecurityForQuery():
    """
    Open Context has 'raw' queries that use PostgresSQL functions to improve performance
    It represents a bit of a security risk for SQL injection attacks.
    So these methods should not be used unless a passed UUID parameter
    is already known to be safe through use in Django's normal querying model
    """
    def __init__(self):
        self.seems_safe = False

    def check_uuid_saftey(self, uuid):
        """ Checks that a UUID only has a limited range of characters so as to reduce
            potential of SQL injecttion attacks.
            This is not fool-proof, so the methods in this class should ONLY
            be used if a uuid parameter is already known to be OK through a
            normal query through Django's normal querying model
        """
        uuid = uuid.strip()
        if re.match(r'^[a-zA-Z0-9][ A-Za-z0-9_-]*$', uuid):
            self.seems_safe = True
            return uuid
        else:
            self.seems_safe = False
            return False
