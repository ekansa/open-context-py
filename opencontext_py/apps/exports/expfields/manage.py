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

    def change_field_number(self, table_id, old_field_num, new_field_num):
        """ changes the field number to a new field number,
            this will change field numbering for the whole table
            so it gets complicated
        """
        # first put the field we're moving into a temporary location
        # for the time being it will be field_num -1
        to_move_field = None
        to_move_f_list = ExpField.objects\
                                 .filter(table_id=table_id,
                                         field_num=old_field_num)[:1]
        if len(to_move_f_list) > 0:
            # temporarily save the to_move_field to field_num -1
            to_move_field = to_move_f_list[0]
            to_move_field.field_num = -1
            to_move_field.save()
            # now temporarily move cell records for the to_move_field to field_num -1
            num_updated = ExpCell.objects\
                                 .filter(table_id=table_id,
                                         field_num=old_field_num)\
                                 .update(field_num=-1)
            print('Staged move of ' + str(num_updated) + ' cell records')
            # now update everything that currently has a new_field_num
            # and higher to increment up 1 so we make space to for
            # the field to be moved.
            # NOTE! Need to order by cells in descending order of field_nums
            # so we don't get update a cell into a field that's is already occupied
            move_fields = ExpField.objects\
                                  .filter(table_id=table_id,
                                          field_num__gte=new_field_num)\
                                  .order_by('-field_num')
            for move_field in move_fields:
                act_old_field_num = move_field.field_num
                act_new_field_num = act_old_field_num + 1
                # mass update the cell records to add 1 to the field_num
                if act_old_field_num != old_field_num:
                    num_move_cells = ExpCell.objects\
                                            .filter(table_id=table_id,
                                                    field_num=act_old_field_num)\
                                            .update(field_num=act_new_field_num)
                    message = 'Shifted ' + str(num_move_cells) + ' from field: '
                    message += str(act_old_field_num) + ' to: ' + str(act_new_field_num)
                    print(message)
                    move_field.field_num = act_new_field_num
                    print('Completed moving field: ' + str(act_old_field_num) + ' to ' + str(act_new_field_num))
                else:
                    # delete the move field, since we have it stored in
                    # memory and in field_num -1
                    move_field.delete()
            # now, finally move the field we set aside to
            # its new field number
            num_updated = ExpCell.objects\
                                 .filter(table_id=table_id,
                                         field_num=-1)\
                                 .update(field_num=new_field_num)
            print('Completed move of ' + str(num_updated) + ' cell records')
            # now delete the field record for new_field_num,
            # since it was copied to have a new_field_num + 1 field_num
            ok = ExpField.objects\
                         .filter(table_id=table_id,
                                 field_num=new_field_num)\
                         .delete()
            # now save the field to be moved with the appropriate field number made vacant above
            to_move_field.field_num = new_field_num
            to_move_field.save()
            print('Completed move of field: ' + str(old_field_num) + ' to: ' + str(new_field_num))
            # now that is done, we do some clean up to make sure
            # the field numbers have no gaps
            print('Doing final checks and cleanup...')
            self.update_field_numbering(table_id)

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
