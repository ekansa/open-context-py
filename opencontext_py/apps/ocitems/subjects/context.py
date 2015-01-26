from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.entities.entity.models import Entity


# Some functions for interacting with subjects by context
class Context():
    """ Class for managing subject contexts, especially for lookups """
    def __init__(self):
        self.entity = False

    def context_dereference(self, context):
        """ looks up a context, described as a '/' seperated list of labels """
        ent = Entity()
        output = False
        try:
            subject = Subject.objects.filter(context=context)[:1]
        except Subject.DoesNotExist:
            subject = False
        if subject is not False:
            if len(subject) == 1:
                output = ent.dereference(subject[0].uuid)
                self.entity = ent
        return output

    def get_context_from_id(self, identifier):
        """ Returns the context path from an identifier, including a slug """
        output = False
        ent = Entity()
        found = ent.dereference(identifier)
        if found:
            print(str(ent.uuid))
            try:
                sub_obj = Subject.objects.get(str(ent.uuid))
            except Subject.DoesNotExist:
                sub_obj = False
            if sub_obj is not False:
                output = sub_obj.context
        return output
