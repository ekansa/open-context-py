
from opencontext_py.apps.all_items import configs



def get_request_user_permissions(request, man_obj, null_request_ok=False):
    """Provides (ok_view, ok_edit) tuple for a manifest object """
    if not man_obj:
        # No item to determine permissions
        return None, None

    if request is None:
        if null_request_ok:
            # We're not doing this in the context of an HTTP request,
            # but via the terminal. Make the permissions OK.
            return True, True
        return None, None

    if request.user.is_superuser:
        # Super-users get to do everything.
        return True, True
    
    if str(man_obj.uuid) == configs.OPEN_CONTEXT_PROJ_UUID:
        # All users can always see the Open Context project item, but
        # only super users can ever edit.
        return True, False
    
    if (man_obj.item_type != 'projects' 
        and str(man_obj.project.uuid) == configs.OPEN_CONTEXT_PROJ_UUID):
        # All users can always see items in the Open Context project, but
        # only super users can ever edit.
        return True, False

    # Get the view group and edit groups for this current item. 
    # If the items lack their own permissions, check with their parent
    # projects.
    view_group_id = man_obj.meta_json.get('view_group_id',
        man_obj.project.meta_json.get('view_group_id')
    )
    edit_group_id = man_obj.meta_json.get('edit_group_id',
        man_obj.project.meta_json.get('edit_group_id')
    )

    if not request.user.is_authenticated:
        if view_group_id:
            # We require a view group, but the user is not
            # authenticated
            return False, False
        # Non-authenticated view is OK, but never edit.
        return True, False
    
    if edit_group_id:
        allow_edit = request.user.groups.filter(id=edit_group_id).exists()
    else:
        allow_edit = False
   
    if allow_edit:
        # If you can edit, you can also view.
        return True, True
    
    if not view_group_id:
        # No view group specified to limit views, so skip out.
        return True, False
    
    allow_view = request.user.groups.filter(id=view_group_id).exists()
    return allow_view, False
    