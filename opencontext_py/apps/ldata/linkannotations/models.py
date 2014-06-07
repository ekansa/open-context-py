import hashlib
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.libs.general import LastUpdatedOrderedDict


# This class stores linked data annotations made on the data contributed to open context
class LinkAnnotation(models.Model):
    # predicates indicating that a subject has an object that is a broader, more general class or property
    # used for establising hierarchy relations among oc-predicates and oc-types
    # these relations are needed for look ups in the faceted search
    PREDS_SBJ_IS_SUB_OF_OBJ = ['skos:broader',
                               'skos:broaderTransitive',
                               'skos:broadMatch',
                               'rdfs:subClassOf',
                               'rdfs:subPropertyOf']

    # predicates indicating that a subject has an object that is narrower (a subclass)
    PREDS_SBJ_IS_SUPER_OF_OBJ = ['skos:narrower',
                                 'skos:narrowerTransitive',
                                 'skos:narrowMatch']

    hash_id = models.CharField(max_length=50, primary_key=True)
    subject = models.CharField(max_length=200, db_index=True)
    subject_type = models.CharField(max_length=50)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    predicate_uri = models.CharField(max_length=200, db_index=True)
    object_uri = models.CharField(max_length=200, db_index=True)
    creator_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of project_uuids and contexts
        """
        hash_obj = hashlib.sha1()
        concat_string = self.subject + " " + self.predicate_uri + " " + self.object_uri
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(LinkAnnotation, self).save()

    class Meta:
        db_table = 'link_annotations'


class LinkRecursion():
    """
    Does recursive look ups on link annotations, especially to find hierarchies
    """
    def __init__(self):
        self.parent_entities = []

    def get_jsonldish_entity_parents(self, identifier):
        """
        Gets parent concepts for a given URI or UUID identified entity
        returns a list of dictionary objects similar to JSON-LD expectations
        This is useful for faceted search
        """
        output = False
        raw_parents = self.get_entity_parents(identifier)
        if(len(raw_parents) > 0):
            output = []
            # reverse the order of the list, to make top most concept
            # first
            parents = raw_parents[::-1]
            for par_id in parents:
                ent = Entity()
                found = ent.dereference(par_id)
                if(found):
                    p_item = LastUpdatedOrderedDict()
                    p_item['id'] = ent.uri
                    p_item['slug'] = ent.slug
                    p_item['label'] = ent.label
                    output.append(p_item)
        return output

    def get_entity_parents(self, identifier):
        """
        Gets parent concepts for a given URI or UUID identified entity
        """
        p_for_superobjs = LinkAnnotation.PREDS_SBJ_IS_SUB_OF_OBJ
        p_for_subobjs = LinkAnnotation.PREDS_SBJ_IS_SUPER_OF_OBJ
        alt_identifier = identifier
        # a little something to allow searches of either UUIDs or full URIs
        if(len(identifier) > 8):
            if(identifier[:7] == 'http://' or identifier[:8] == 'https://'):
                alt_identifier = URImanagement.get_uuid_from_oc_uri(identifier)
                if(alt_identifier is False):
                    alt_identifier = identifier
        try:
            # look for superior items in the objects of the assertion
            superobjs_anno = LinkAnnotation.objects.filter(Q(subject=identifier) | Q(subject=alt_identifier),
                                                           predicate_uri__in=p_for_superobjs)[:1]
            if(len(superobjs_anno) < 1):
                superobjs_anno = False
        except LinkAnnotation.DoesNotExist:
            superobjs_anno = False
        if(superobjs_anno is not False):
            parent_id = superobjs_anno[0].object_uri
            if(parent_id.count('/') > 1):
                oc_uuid = URImanagement.get_uuid_from_oc_uri(parent_id)
                if(oc_uuid is not False):
                    parent_id = oc_uuid
                if(parent_id not in self.parent_entities):
                    self.parent_entities.append(parent_id)
            self.parent_entities = self.get_entity_parents(parent_id)
        try:
            """
            Now look for superior entities in the subject, not the object
            """
            supersubj_anno = LinkAnnotation.objects.filter(Q(object_uri=identifier) | Q(object_uri=alt_identifier),
                                                           predicate_uri__in=p_for_subobjs)[:1]
            if(len(supersubj_anno) < 1):
                supersubj_anno = False
        except LinkAnnotation.DoesNotExist:
            supersubj_anno = False
        if(supersubj_anno is not False):
            parent_id = supersubj_anno[0].subject
            if(parent_id.count('/') > 1):
                oc_uuid = URImanagement.get_uuid_from_oc_uri(parent_id)
                if(oc_uuid is not False):
                    parent_id = oc_uuid
                if(parent_id not in self.parent_entities):
                    self.parent_entities.append(parent_id)
            self.parent_entities = self.get_entity_parents(parent_id)
        return self.parent_entities
