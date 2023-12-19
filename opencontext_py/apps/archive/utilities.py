import os
import json
import codecs

from django.conf import settings

from opencontext_py.apps.all_items.models import (
    AllManifest,
)

ARCHIVE_LOCAL_ROOT_PATH = settings.STATIC_EXPORTS_ROOT
PROJECT_ARCHIVE_LOCAL_DIR_PREFIX = 'files'

PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME = 'zenodo-oc-files.json'


def make_full_path_filename(path, file_name):
    """ makes a full filepath and file name string """
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, file_name)


def save_serialized_json(path, file_name, dict_obj):
    """ saves a data in the appropriate path + file """
    dir_file = make_full_path_filename(path, file_name)
    json_output = json.dumps(
        dict_obj,
        indent=4,
        ensure_ascii=False,
    )
    file = codecs.open(dir_file, 'w', 'utf-8')
    file.write(json_output)
    file.close()


def get_file_count_and_size(path):
    """ returns the file count and size of a directory """
    file_count = 0
    total_size = 0

    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            file_count += 1
            total_size += os.path.getsize(file_path)

    return file_count, total_size


def get_sub_directories(path):
    """Gets a list of subdirectories in a directory"""
    os.makedirs(path, exist_ok=True)
    subdirectories = [
        d for d in os.listdir(path)
        if os.path.isdir(os.path.join(path, d))
    ]
    return subdirectories


def get_project_dir_partition_number(dir_name):
    """Gets the partition number from a directory name"""
    if not isinstance(dir_name, str):
        return None
    if not dir_ex[0].startswith(PROJECT_ARCHIVE_LOCAL_DIR_PREFIX):
        return None
    if not '---' in dir_name:
        return None
    dir_ex = dir_name.split('---')
    dir_ex2 = dir_ex[0].split('-')
    if len(dir_ex2) < 2:
        return None
    try:
        partition_num = int(float(dir_ex2[1]))
    except:
        partition_num = None
    return partition_num


def get_maximum_dir_partition_number_for_project_dirs(project_dirs):
    """Gets the maximum partition number from a list of project directories"""
    if not isinstance(project_dirs, list):
        return None
    max_partition_num = None
    for act_dir in project_dirs:
        partition_num = get_project_dir_partition_number(act_dir)
        if partition_num is None:
            continue
        if max_partition_num is None or partition_num > max_partition_num:
            max_partition_num = partition_num
    return max_partition_num


def sort_project_dirs(raw_project_dirs):
    """Sorts a list of project directories by partition number"""
    if not isinstance(raw_project_dirs, list):
        return []
    tuple_list = []
    for act_dir in raw_project_dirs:
        partition_num = get_project_dir_partition_number(act_dir)
        if partition_num is None:
            continue
        dir_tuple = (partition_num, act_dir,)
        tuple_list.append(dir_tuple)
    sorted_dirs = []
    for tuple_dir in sorted(tuple_list, key=lambda x: x[0]):
        sorted_dirs.append(tuple_dir[1])
    return sorted_dirs


def get_project_binaries_dirs(
    project_uuid,
    files_prefix=PROJECT_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """ gets directories associated with a project id """
    raw_project_dirs = []
    for act_dir in get_sub_directories(root_path):
        if not '---' in act_dir or not act_dir.startswith(files_prefix):
            continue
        act_ex = act_dir.split('---')
        if project_uuid != act_ex[-1]:
            continue
        # the first part of a the name should be like 'files-1-by'
        # the second part, after the '---' should be the project_uuid
        raw_project_dirs.append(act_dir)
    # Now sort the directories by partition number
    project_dirs = sort_project_dirs(raw_project_dirs)
    return project_dirs


def get_maximum_dir_partition_number_for_project(
    project_uuid,
    files_prefix=PROJECT_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Gets the maximum partition number from a list of project directories"""
    project_dirs = get_project_binaries_dirs(
        project_uuid=project_uuid,
        files_prefix=files_prefix,
        root_path=root_path,
    )
    return get_maximum_dir_partition_number_for_project_dirs(project_dirs)


def gather_project_dir_file_manifest(
    project_uuid,
    files_prefix=PROJECT_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """ gathers the file manifest for a project """
    project_dirs = get_project_binaries_dirs(
        project_uuid=project_uuid,
        files_prefix=files_prefix,
        root_path=root_path,
    )
    all_files = []
    for act_dir in project_dirs:
        act_path = os.path.join(root_path, act_dir)
        dir_file = os.path.join(act_path, PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME)
        if not os.path.exists(dir_file):
            continue
        dir_dict = json.load(open(dir_file))
        all_files += dir_dict.get('files', [])
    return all_files


def make_project_part_license_dir_name(
    part_num,
    license_uri,
    project_uuid,
    files_prefix=PROJECT_ARCHIVE_LOCAL_DIR_PREFIX,
):
    """ makes a directory name for a given project, license, and directory_number """
    license_uri = AllManifest().clean_uri(license_uri)
    lic_part = license_uri.split('/')[-1]
    act_dir = f'{files_prefix}-{str(part_num)}-{lic_part}---{project_uuid}'
    return act_dir


def make_project_part_license_dir_path_and_name(
    part_num,
    license_uri,
    project_uuid,
    files_prefix=PROJECT_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """ makes a directory name for a given project, license, and directory_number """

    act_dir = make_project_part_license_dir_name(
        part_num=part_num,
        license_uri=license_uri,
        project_uuid=project_uuid,
        files_prefix=files_prefix,
    )
    act_path = os.path.join(root_path, act_dir)
    return act_path