from django.db import models
from opencontext_py.apps.ldata.linkentities.models import LinkEntity, LinkEntityGeneration
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.manage import LinkAnnoManagement
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.contexts.models import SearchContext


# This class has methods to create and update linked data entities
class LinkEntityManage():

    SENSITIVE_VOCABS = ['http://opencontext.org/vocabularies/']

    def __init__(self):
        self.super_user = False
        self.errors = {'uri': False,
                       'params': False}
        self.response = {}
        self.sensitive_ns = self.SENSITIVE_VOCABS
        item_context_obj = ItemContext()
        search_context_obj = SearchContext()
        self.build_sensitive_list(item_context_obj.context)
        self.build_sensitive_list(search_context_obj.context)
        self.uri = False

    def is_uri_sensitive(self, uri):
        """ checks to see if a URI is in a sensitive vocabulary """
        is_sensitive = False
        for check_ns in self.sensitive_ns:
            if check_ns in uri:
                is_sensitive = True
                break
        return is_sensitive

    def add_update(self, post_data):
        """ Creates or updates a linked data entity """
        ok = True
        uri = False
        label = False
        vocab_uri = False
        alt_label = False
        ent_type = 'class'
        note = ''
        action = 'attempted creation or update'
        sent_uri = uri
        sent_label = label
        if 'uri' in post_data:
            uri = post_data['uri']
            sent_uri = uri
            if not self.validate_web_uri(uri):
                # must be a full web uri to use
                note += '"' + uri + '" needs to be valid Web URI. '
                uri = False
        if 'label' in post_data:
            label = post_data['label']
            sent_label = label
            alt_label = label  # default for alt-label is label
            if len(label) < 1:
                note += 'The entity label cannot be blank. '
                label = False
        if 'alt_label' in post_data:
            if len(post_data['alt_label']) > 0:
                alt_label = post_data['alt_label']
        if 'ent_type' in post_data:
            ent_type = post_data['ent_type']
        if 'vocab_uri' in post_data:
            vocab_uri = post_data['vocab_uri']
            if not self.validate_web_uri(vocab_uri)\
               and ent_type != 'vocabulary':
                    # vocab_uri is not a full uri, so suggest one
                    # based on the URI for the request
                    vocab_uri = self.suggest_vocabulary(uri)
            elif not self.validate_web_uri(vocab_uri)\
               and ent_type == 'vocabulary':
                vocab_uri = uri
            else:
                pass
        if uri is not False \
           and label is not False \
           and vocab_uri is not False:
            le_gen = LinkEntityGeneration()
            uri = le_gen.make_clean_uri(uri)
            if uri != vocab_uri:
                # get the varient of the vocab_uri that's actually in use
                # returns false if a varient can't be found
                vocab_uri = self.check_vocab_uri(vocab_uri)
                if vocab_uri is False:
                    # cannot find a varient for this vocabulary uri
                    vocab_ok = False
                else:
                    vocab_ok = True
            elif ent_type == 'vocabulary':
                vocab_ok = True
            else:
                vocab_ok = False
            if vocab_ok:
                ok = True
                try:
                    action = 'edit-update'
                    le = LinkEntity.objects.get(uri=uri)
                except LinkEntity.DoesNotExist:
                    action = 'add-create'
                    le = LinkEntity()
                    le.uri = uri
                # now add information to save
                le.label = label
                le.alt_label = alt_label
                le.ent_type = ent_type
                le.vocab_uri = vocab_uri
                # print('ENT TYPE!!!! ' + str(len(uri)))
                le.save()
                uri = le.uri  # in case the URI changed because of validation changes
            else:
                ok = False
                note += 'Must first create a record for the vocabulary. '
        else:
            ok = False
            note += 'Missing data required for this action. '
        self.response = {'action': action,
                         'uri': sent_uri,
                         'label': sent_label,
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def suggest_vocabulary(self, uri):
        """ suggests a vocabulary based on
            the content of the URI
        """
        vocab_uri = False
        le_gen = LinkEntityGeneration()
        uri = le_gen.make_clean_uri(uri)
        if '/' in uri:
            uri_ex = uri.split('/')
            last_part = '/' + uri_ex[-1]
            uri_prefix = uri.replace(last_part, '')
            print('Checking uri prefix: ' + uri_prefix)
            le_examps = LinkEntity.objects\
                                  .filter(uri__contains=uri_prefix)
            if len(le_examps) > 0:
                vocab_uris = []
                for le_ex in le_examps:
                    if le_ex.vocab_uri not in vocab_uris:
                        # doing this to make sure we have an unambiguous URI
                        vocab_uris.append(le_ex.vocab_uri)
                if len(vocab_uris) == 1:
                    # the uri prefix was not ambiguous, so we can use it
                    vocab_uri = vocab_uris[0]
        return vocab_uri

    def check_vocab_uri(self, vocab_uri):
        """ checks to see if the vocabulary
            has a linked entity record, returns
            a varient that is actually in use        
        """
        if isinstance(vocab_uri, str):
            vocabs_list = [vocab_uri]
            if vocab_uri[-1] == '/':
                # make a varient without the last slash
                vocabs_list.append(vocab_uri[:-1])
            else:
                # make a varient with a last slash
                vocabs_list.append((vocab_uri + '/'))
            le = LinkEntity.objects\
                           .filter(uri__in=vocabs_list)[:1]
            if len(le) > 0:
                # found a varient, return vocab_uri as a
                # varient that actually is in use
                vocab_uri = le[0].uri
            else:
                # vocaulary doesn't exist
                vocab_uri = False
        else:
            vocab_uri = False
        return vocab_uri

    def validate_web_uri(self, uri):
        """ checks to see if a uri is a valid web uri """
        is_valid = False
        if 'http://' in uri \
           or 'https://' in uri:
            is_valid = True
        return is_valid

    def build_sensitive_list(self, context):
        """ builds a list of sensitive namespaces
            that need super user status to edit
        """
        for prefix, uri in context.items():
            if 'http://' in uri or 'https://' in uri:
                if uri not in self.sensitive_ns:
                    self.sensitive_ns.append(uri)

    def replace_uri(self, old_uri, new_uri, new_label, new_vocab_uri):
        """ replaces an old URI and old Vocab URI
            with a new URI and a new vocab URI,
            changes both objects in the link_entity model
            and the link_annotation model

from opencontext_py.apps.ldata.linkentities.manage import LinkEntityManage
lem = LinkEntityManage()
old_uri = 'http://www.cidoc-crm.org/rdfs/cidoc-crm#P45F.consists_'
new_uri = 'http://erlangen-crm.org/current/P45_consists_of'
new_label = 'Consists of'
new_vocab_uri = 'http://www.cidoc-crm.org/cidoc-crm/'
lem.replace_uri(old_uri, new_uri, new_label, new_vocab_uri)

from opencontext_py.apps.ldata.linkentities.manage import LinkEntityManage
lem = LinkEntityManage()
old_uri = 'http://www.eol.org/pages/695'
new_uri = 'http://eol.org/pages/695'
new_label = 'Aves'
new_vocab_uri = 'http://eol.org/'
lem.replace_uri(old_uri, new_uri, new_label, new_vocab_uri)

        """
        try:
            old_ent = LinkEntity.objects.get(uri=old_uri)
        except LinkEntity.DoesNotExist:
            old_ent = False
        if old_ent is not False:
            # now change to use the new information
            new_ent = old_ent
            old_ent.delete()
            try:
                new_ent_exists = LinkEntity.objects.get(uri=new_uri)
            except LinkEntity.DoesNotExist:
                # replace the old ent with the new ent
                new_ent.uri = new_uri
                new_ent.label = new_label
                new_ent.vocab_uri = new_vocab_uri
                new_ent.save()
        # do this even if the old item does not exist
        la_manage = LinkAnnoManagement()
        la_manage.replace_subject_uri(old_uri,
                                      new_uri)
        la_manage.replace_predicate_uri(old_uri,
                                        new_uri)
        la_manage.replace_object_uri(old_uri,
                                     new_uri)
