import json
from unidecode import unidecode
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell


# Methods to manage export table fields
class ExpFieldManage():

    """ Methods to manage export table field.

    Sometimes, there's a need to remove or merge
    certain fields from an export table. These methods
    accomplish those tasks.

from opencontext_py.apps.exports.expfields.manage import ExpFieldManage
xpFieldMan = ExpFieldManage()
table_id = 'a1c445f9-6bba-48c9-8a56-e5f49aae6c61'
old_to_new_map = xpFieldMan.map_old_to_new_fields(
    table_id,
    old_field_num=36,
    new_field_num=29,
    old_to_new_map=None
)
print(str(old_to_new_map))
old_to_new_map = xpFieldMan.map_old_to_new_fields(
    table_id,
    old_to_new_map={28:74, 36:29, 40:75, 44:76, 52:77}
)
xpFieldMan.change_field_number(table_id, old_to_new_map={28:74, 36:29, 40:75, 44:76, 52:77})

    """

    def __init__(self):
        self.table_id = False
        self.json_list_merge = False
        self.merge_delim = '; '
        self.predicate_related_fields = 'skos:related'

    def consolidate_same_field_labels(self, table_id):
        """ consolidates fields with the same label """
        label_fields = {}
        tab_fields = ExpField.objects.filter(table_id=table_id)
        for t_field in tab_fields:
            label = t_field.label.strip()
            if label not in label_fields:
                label_fields[label] = []
            label_fields[label].append(t_field.field_num)
        for label, fields in label_fields.items():
            if len(fields) > 1:
                # this label is used for more than 1 field!
                # first, minimum field number is the one to keep
                keep_field_num = min(fields)
                merge_remove_field_nums = []
                for field_num in fields:
                    if field_num > keep_field_num:
                        # add the other field numbers to be the ones to remove
                        merge_remove_field_nums.append(field_num)
                message = 'Merge ' + str(len(merge_remove_field_nums)) + ' fields into: '
                message += str(unidecode(label)) + '(' + str(keep_field_num) + ')'
                print(message)
                self.merge_field_cells(table_id, keep_field_num, merge_remove_field_nums)
                self.merge_fields(table_id, keep_field_num, merge_remove_field_nums)
        self.update_field_numbering(table_id)

    def merge_fields(self, table_id, keep_field_num, merge_remove_field_nums):
        """ merges fields, first it merges the values of
            cells from different fields (on a row-by-row basis)

            then it consolidates field metadata together to show
            provenance
        """
        keep_field_list = ExpField.objects.filter(table_id=table_id,
                                                  field_num=keep_field_num)[:1]
        if len(keep_field_list) > 0:
            related_fields = []
            keep_field = keep_field_list[0]
            if 'rdfs:isDefinedBy' in keep_field.rel_ids:
                related_fields.append(keep_field.rel_ids['rdfs:isDefinedBy'])
            remove_fields = ExpField.objects.filter(table_id=table_id,
                                                    field_num__in=merge_remove_field_nums)
            for rem_field in remove_fields:
                if 'rdfs:isDefinedBy' in rem_field.rel_ids:
                    if rem_field.rel_ids['rdfs:isDefinedBy'] not in related_fields:
                        # only add the predicate if not already in
                        related_fields.append(rem_field.rel_ids['rdfs:isDefinedBy'])
            if len(related_fields) > 1:
                # case where multiple predicates relate to this field
                if 'rdfs:isDefinedBy' in keep_field.rel_ids:
                    # remove the 'isDefinedBy' property, because it is not valid
                    keep_field.rel_ids.pop('rdfs:isDefinedBy', None)
                keep_field.rel_ids[self.predicate_related_fields] = related_fields
            elif len(related_fields) == 1:
                # case with only 1 predicate to define the field
                keep_field.rel_ids['rdfs:isDefinedBy'] = related_fields[0]
            print('Related fields: ' + str(keep_field.rel_ids))
            keep_field.save()
            for rem_field in remove_fields:
                # delete the old fields once the merge is done
                rem_field.delete()

    def merge_field_cells(self, table_id, keep_field_num, merge_remove_field_nums):
        """ merges data into a keep field from the merge_remove_field
            then it deletes the merge_remove_field
        """
        if not isinstance(merge_remove_field_nums, list):
            merge_remove_field_nums = [merge_remove_field_nums]
        # get all the rows where these the keep and merge-remove fields
        # are used for this table
        act_fields = [keep_field_num] + merge_remove_field_nums
        act_cells = ExpCell.objects.filter(table_id=table_id,
                                           field_num__in=act_fields)\
                                   .order_by('row_num')\
                                   .distinct('row_num')
        for act_cell in act_cells:
            # now get cells for this row in the fields to be merged and removed
            act_row = act_cell.row_num
            print('Merge to field: ' + str(keep_field_num) + ', row: ' + str(act_cell.row_num))
            # cell_values is a list of values that are getting merged together
            cell_values = []
            # gets all the cells with values for the keep and remove fields
            # for this particular row
            act_row_cells = ExpCell.objects.filter(table_id=table_id,
                                                   field_num__in=act_fields,
                                                   row_num=act_row)\
                                           .order_by('field_num')
            keep_cell = None
            for a_row_cell in act_row_cells:
                cell_values = self.add_cell_record_to_cell_values_list(cell_values,
                                                                       a_row_cell.record)
                if keep_cell is None:
                    # the first cell is to be kept
                    keep_cell = a_row_cell
                    # make sure the first cell is assigned to the correct (keep) field number
                    keep_cell.field_num = keep_field_num
            if keep_cell is not None and len(cell_values) > 0:
                keep_cell.record = self.merge_delim.join(cell_values)
                keep_cell.save()
            # now delete all the old cells that are in fields to be removed
            ExpCell.objects\
                   .filter(table_id=table_id,
                           field_num__in=merge_remove_field_nums,
                           row_num=act_row)\
                   .delete()

    def delete_fields_after(self, table_id, last_keep_field_num):
        """ Deletes field_num greter than the
            last_keep_field_num
        """
        delete_field_nums = []
        del_fields = ExpField.objects\
                             .filter(table_id=table_id,
                                     field_num__gt=last_keep_field_num)
        for del_field in del_fields:
            delete_field_nums.append(del_field.field_num)
        self.delete_fields_list(table_id, delete_field_nums)

    def delete_fields_list(self, table_id, delete_field_nums):
        """ Deletes fields in a list of field numbers """
        if isinstance(delete_field_nums, int):
            # make 1 integer a list
            delete_field_nums = [delete_field_nums]
        if isinstance(delete_field_nums, list):
            if len(delete_field_nums) > 0:
                # we have a list, so use in a delete queries
                print('Deleting ' + str(len(delete_field_nums)) + ' fields...')
                num_del_cells = ExpCell.objects\
                                       .filter(table_id=table_id,
                                               field_num__in=delete_field_nums)\
                                       .delete()
                print('Deleted ' + str(num_del_cells) + ' cell records.')
                num_del_fields = ExpField.objects\
                                         .filter(table_id=table_id,
                                                 field_num__in=delete_field_nums)\
                                         .delete()
                print('Finished deleting ' + str(num_del_fields) + ' fields.')
                print('Checking and cleaning up table...')
                self.update_field_numbering(table_id)

    def map_old_to_new_fields(
        self,
        table_id,
        old_field_num=None,
        new_field_num=None,
        old_to_new_map=None
    ):
        """Makes a dict of {old_field_num: new_field_num} to map updates to a table field num order"""
        if old_to_new_map is None:
            old_to_new_map = {old_field_num: new_field_num}
            
        # Get the fields for the table we want to modify.
        fields = ExpField.objects.filter(table_id=table_id).order_by('field_num')

        # Get the maximum field number, which is from the last object because we
        # ordered the query set by field_num.
        max_field_num = fields.last().field_num

        # Now do some checks to make sure our old_to_new_map dictionary
        # is OK.
        new_field_nums = set()
        for old, new in old_to_new_map.items():
            # Make sure that the new_field_num is no greater than
            # the maximum field number
            if old > max_field_num:
                raise ValueError('Field_num {} does not exist in {}'.format(old, table_id))
            if new > max_field_num:
                raise RuntimeWarning('Field_num {} does not exist in {}, setting to {}'.format(
                        new,
                        table_id,
                        max_field_num
                    )
                )
                old_to_new_map[old] = max_field_num
            new_field_nums.add(old_to_new_map[old])
        assert len(old_to_new_map) == len(new_field_nums), 'Invalid old_to_new mappings'
       
        # Now iterate through and create mappings for all the fields. This
        # makes sure that the old_to_new_map dictionary completely specifies
        # all of the field_numbers, including the ones that DON'T change.
        new_field_num = 0
        for field in fields:
            if field.field_num in old_to_new_map:
                continue
            # Get the first unused new_index in the range of available
            # values.
            for new_field_num in range(1, (max_field_num + 1)):
                if not new_field_num in new_field_nums:
                    break
            new_field_nums.add(new_field_num)
            old_to_new_map[field.field_num] = new_field_num
        
        # Do some checking to make sure the logic worked and we have a complete
        # set of mappings.
        all_old = set()
        all_new = set()
        for old, new in old_to_new_map.items():
            all_old.add(old)
            all_new.add(new)
        # The set of old field number and new field numbers needs
        # to be identical, otherwise we did something horrible.
        assert all_old == all_new, 'The field mappings failed!'
        return old_to_new_map

    def change_field_number(
        self,
        table_id,
        old_field_num=None,
        new_field_num=None,
        old_to_new_map=None
    ):
        """ changes the field number to a new field number,
            this will change field numbering for the whole table
            so it gets complicated
        """
        old_to_new_map = self.map_old_to_new_fields(
            table_id,
            old_field_num=old_field_num,
            new_field_num=new_field_num,
            old_to_new_map=old_to_new_map
        )
        # Now move the fields that are getting moved to a new order.
        # First, set the new_field_num to be temporarily a negative number
        # so as to make sure we don't overwrite things by shifting them
        # around.
        for act_old_field_num, act_new_field_num in old_to_new_map.items():
            if (act_old_field_num == act_new_field_num):
                # No change in the fields.
                continue
            self.change_field_cell_field_numbers(
                table_id,
                act_old_field_num,
                (act_new_field_num * -1)
            )
        # Now finish reorder the field numbers, changing the temporary
        # order back to the preferred final order
        for act_old_field_num, act_new_field_num in old_to_new_map.items():
            if (act_old_field_num == act_new_field_num):
                # No change in the fields.
                continue
            self.change_field_cell_field_numbers(
                table_id,
                (act_new_field_num * -1),
                act_new_field_num
            )

    def change_field_cell_field_numbers(self, table_id, old_num, new_num):
        num_move_cells = ExpCell.objects.filter(
            table_id=table_id,
            field_num=old_num
        ).update(field_num=new_num)
        message = 'Shifted {} from field: {} to {}'.format(num_move_cells, old_num, new_num)
        ok_field = ExpField.objects.filter(
            table_id=table_id,
            field_num=old_num
        ).update(field_num=new_num)
        if old_num > 0 and new_num < 0:
            change_type = '[Temporary Update]'
        else:
            change_type = 'Finished Update'
        message += '\n{} of {} from field: {} to {}'.format(change_type, ok_field, old_num, new_num)
        print(message)

    def update_field_numbering(self, table_id):
        """ updates the numbering for fields after the
            table was modified
        """
        fields = ExpField.objects\
                         .filter(table_id=table_id)\
                         .order_by('field_num')
        expected_field_num = 1
        for field in fields:
            print('Check expected: ' + str(expected_field_num))
            print('against actual: ' + str(field.field_num))
            if field.field_num > expected_field_num:
                # we are missing some fields, need
                # to renumber to the expected field number
                num_updated = ExpCell.objects\
                                     .filter(table_id=table_id,
                                             field_num=field.field_num)\
                                     .update(field_num=expected_field_num)
                print('Updated ' + str(num_updated) + ' cells to expected field num.')
                # now save the field_num to the expected value
                field.field_num = expected_field_num
                field.save()
            # the next expected field num will be 1 higher than the current
            expected_field_num = field.field_num + 1

    def add_cell_record_to_cell_values_list(self, cell_values, record):
        """ adds non-blank strings to the cell values list """
        if isinstance(record, str):
            record = record.strip()
            if len(record) > 0:
                cell_values.append(record)
        return cell_values
