from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.datatypeclass import DescriptionDataType
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell


# Methods for adding metadata to new manifest items
class ManifestMetadata():

    def __init__(self, source_id, project_uuid):
        self.source_id = source_id
        self.project_uuid = project_uuid
        self.metadata_fields = None
        self.metadata_field_nums = []
        self.manifest_metadata_fields = None
        self.get_metadata_fields()
        # fields where a UUID value exists
        self.uuid_fields = [
            'uuid',
            '_uuid',  # used in Kobotoolbox
            'UUID'
        ]

    def get_metadata_fields(self):
        """ gets metadata fields describing items in a manifest field list
            this will be used to provide some sup_json information in the event
            that a new manifest object is created
        """
        meta_fields = ImportField.objects\
                                 .filter(source_id=self.source_id,
                                         field_type='metadata')\
                                 .order_by('field_num')
        if len(meta_fields) > 0:
            self.metadata_field_nums = []
            self.metadata_fields = LastUpdatedOrderedDict()
            for meta_field in meta_fields:
                self.metadata_fields[meta_field.field_num] = meta_field
                self.metadata_field_nums.append(meta_field.field_num)
        return self.metadata_fields

    def get_metadata_fields_for_field_list(self, manifest_field_list):
        """ gets metadata fields describing items in a manifest field list
            this will be used to provide some sup_json information in the event
            that a new manifest object is created
        """
        
        
        self.manifest_metadata_fields = LastUpdatedOrderedDict()
        meta_field_annos = ImportFieldAnnotation.objects\
                                                .filter(source_id=self.source_id,
                                                        predicate=ImportFieldAnnotation.PRED_METADATA,
                                                        object_field_num__in=manifest_field_list)\
                                                .order_by('object_field_num', 'field_num')
        for meta_anno in meta_field_annos:
            if meta_anno.object_field_num not in self.manifest_metadata_fields:
                self.manifest_metadata_fields[meta_anno.object_field_num] = []
            if meta_anno.field_num in self.metadata_fields:
                self.manifest_metadata_fields[meta_anno.object_field_num].append(meta_anno.field_num)     
        return self.manifest_metadata_fields

    def get_metadata(self, manifest_field_num, row_num):
        """ gets metadata fields describing items in a manifest field list
            this will be used to provide some sup_json information in the event
            that a new manifest object is created
        """
        output = None
        if len(self.metadata_field_nums) > 0:
            imp_meta_recs = ImportCell.objects\
                                      .filter(source_id=self.source_id,
                                              field_num__in=self.metadata_field_nums,
                                              row_num=row_num)\
                                      .exclude(record='')\
                                      .order_by('field_num')
            if len(imp_meta_recs) > 0:
                output = LastUpdatedOrderedDict()
                meta = LastUpdatedOrderedDict()
                ddt = DescriptionDataType()
                if manifest_field_num in self.manifest_metadata_fields:
                    m_type = 'metadata'
                else:
                    m_type = 'rel-metadata'
                for imp_meta_rec in imp_meta_recs:
                    int_val = ddt.validate_integer(imp_meta_rec.record)
                    float_val = ddt.validate_numeric(imp_meta_rec.record)
                    if int_val is not None:
                        act_val = int_val
                    elif float_val is not None:
                        act_val = float_val
                    else:
                        act_val = imp_meta_rec.record
                    if imp_meta_rec.field_num in self.metadata_fields:
                        act_field =  self.metadata_fields[imp_meta_rec.field_num]
                    if act_field.label in meta:
                        # we have this same key already, so make sure its values
                        # are in a list
                        if not isinstance(meta[act_field.label], list):
                            old_val = meta[act_field.label]
                            meta[act_field.label] = [old_val]
                        meta[act_field.label].append(act_val)
                    else:
                         meta[act_field.label] = act_val
                meta['row_num'] = row_num
                output[m_type] = meta
        return output
    
    def get_uuid_from_metadata_dict(self, metadata_dict):
        """ gets a uuid value (if it exists and is valid)
            from a metadata dict
        """
        uuid = None
        if isinstance(metadata_dict, dict):
            if 'metadata' in metadata_dict:
                meta_dict = metadata_dict['metadata']
                for uuid_field in self.uuid_fields:
                    if uuid_field in meta_dict:
                        if isinstance(meta_dict[uuid_field], str):
                            if len(meta_dict[uuid_field]) > 30:
                                if '-' in meta_dict[uuid_field]:
                                    uuid = meta_dict[uuid_field]
                                    print('found uuid to use: ' + uuid)
                                    break
        return uuid
            
