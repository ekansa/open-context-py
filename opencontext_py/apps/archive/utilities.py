import os
import json
import codecs

from zipfile import ZipFile

from django.conf import settings

from opencontext_py.apps.all_items.models import (
    AllManifest,
)

ARCHIVE_LOCAL_ROOT_PATH = settings.STATIC_EXPORTS_ROOT
PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX = 'files'
PROJECT_DATA_ARCHIVE_LOCAL_DIR_PREFIX = 'structured-data'
TABLE_DATA_ARCHIVE_LOCAL_DIR_PREFIX = 'table-data'

PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME = 'zenodo-oc-files.json'
PROJECT_ZIP_FILENAME = 'oc-files.zip'

MAX_DEPOSITION_FILE_COUNT = 98
MAX_DEPOSITION_FILE_SIZE = 45000000000  # 45 GB
ZIP_MEDIA_MANIFEST_THRESHOLD = 500 # 500 media items


def make_full_path_filename(path, filename):
    """ makes a full filepath and file name string """
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, filename)


def load_serialized_json(path, filename):
    dir_file = os.path.join(path, filename)
    if not os.path.exists(dir_file):
        return None
    file_dict = json.load(open(dir_file))
    return file_dict


def save_serialized_json(path, filename, dict_obj):
    """ saves a data in the appropriate path + file """
    dir_file = make_full_path_filename(path, filename)
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


def zip_files(path, file_paths=None, zip_name=PROJECT_ZIP_FILENAME):
    """Create a ZipFile object in write mode and add files to it"""
    if not file_paths:
        file_paths = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.zip'):
                    continue
                if file.endswith('.json'):
                    continue
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
    if not file_paths:
        return None
    zip_path = os.path.join(path, zip_name)
    with ZipFile(zip_path, 'w') as zipf:
        # Iterate over all files in the directory
        for file_path in file_paths:
            # Add the file to the zip archive with its relative path
            rel_path = os.path.relpath(file_path, path)
            zipf.write(file_path, rel_path)
    print(f'Zipped {len(file_paths)} files to: {zip_path}')
    return zip_path, zip_name


def check_if_dir_is_full(path, zip_dir_contents=False):
    """ checks if a directory is full """
    file_count, total_size = get_file_count_and_size(path)
    if not zip_dir_contents and file_count >= (MAX_DEPOSITION_FILE_COUNT + 1):
        # we don't count the manifest file, so allow
        # one more file than the max
        return True
    if total_size >= MAX_DEPOSITION_FILE_SIZE:
        return True
    return False


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
    if not dir_name.startswith(PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX):
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
    files_prefix=PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX,
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
    files_prefix=PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Gets the maximum partition number from a list of project directories"""
    project_dirs = get_project_binaries_dirs(
        project_uuid=project_uuid,
        files_prefix=files_prefix,
        root_path=root_path,
    )
    return get_maximum_dir_partition_number_for_project_dirs(project_dirs)


def gather_project_dir_file_dict_list(
    project_uuid,
    files_prefix=PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
    check_binary_files_present=False,
):
    """ gathers the file manifest for a project """
    project_dirs = get_project_binaries_dirs(
        project_uuid=project_uuid,
        files_prefix=files_prefix,
        root_path=root_path,
    )
    all_file_dicts = []
    for act_dir in project_dirs:
        act_path = os.path.join(root_path, act_dir)
        dir_dict = load_serialized_json(
            path=act_path,
            filename=PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME
        )
        if not dir_dict:
            continue
        if not check_binary_files_present:
            all_file_dicts += dir_dict.get('files', [])
            continue
        # Below we will check to make sure the binary files actually
        # do exist in the directory
        for f_dict in dir_dict.get('files', []):
            filename = f_dict.get('filename')
            if not filename:
                continue
            filepath = os.path.join(act_path, filename)
            if os.path.exists(filepath):
                # Yes, the file is actually present here.
                all_file_dicts.append(f_dict)
    return all_file_dicts


def gather_project_dir_filename_list(
    project_uuid,
    files_prefix=PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
    check_binary_files_present=False,
):
    """ gathers the file manifest for a project """
    all_file_dicts = gather_project_dir_file_dict_list(
        project_uuid=project_uuid,
        files_prefix=files_prefix,
        root_path=root_path,
        check_binary_files_present=check_binary_files_present,
    )
    if not all_file_dicts:
        return []
    filenames = [f_dict.get('filename') for f_dict in all_file_dicts if f_dict.get('filename')]
    return filenames


def make_project_part_license_dir_name(
    part_num,
    license_uri,
    project_uuid,
    files_prefix=PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX,
):
    """ makes a directory name for a given project, license, and directory_number """
    license_uri = AllManifest().clean_uri(license_uri)
    lic_part = license_uri.split('/')[-1]
    try:
        lic_num = float(lic_part)
    except:
        lic_num = None
    if lic_num is not None:
        # we don't want the "4.0" of the "/by/4.0", we want the "by"
        lic_part = license_uri.split('/')[-2]
    act_dir = f'{files_prefix}-{str(part_num)}-{lic_part}---{project_uuid}'
    return act_dir


def make_project_part_license_dir_path(
    part_num,
    license_uri,
    project_uuid,
    files_prefix=PROJECT_FILES_ARCHIVE_LOCAL_DIR_PREFIX,
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


def validate_archive_dir_binaries(act_path, dir_dict=None):
    """ makes sure the all the archive dir actually has all of the files
        it says it has to archive
    """
    if not dir_dict:
        dir_dict = load_serialized_json(
            path=act_path,
            filename=PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME
        )
    if not isinstance(dir_dict, dict):
        print(f'Cannot read an archive contents file in: {act_path}')
        return False, [f'Cannot read an archive contents file in: {act_path}']
    errors = []
    for file_dict in dir_dict.get('files', []):
        filename = file_dict.get('filename')
        if not filename:
            continue
        file_path = os.path.join(act_path, filename)
        if not os.path.exists(file_path):
            errors.append(file_dict)
            print(f'Cannot find {filename} in: {act_path}')
    valid = len(errors) == 0
    return valid, errors


def recommend_zip_archive(proj_license_dict):
    """Recommends whether to zip files described in a project license dict"""
    count = 0
    for _, man_objs in proj_license_dict.items():
        count += len(man_objs)
    if count >= ZIP_MEDIA_MANIFEST_THRESHOLD:
        return True
    return False


def make_project_data_dir_name(
    project_uuid,
    data_prefix=PROJECT_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
):
    """Makes a directory name for a (structured) data export for a given project"""
    return f'{data_prefix}---{project_uuid}'


def make_project_data_dir_path(
    project_uuid,
    data_prefix=PROJECT_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Makes a directory path for a (structured) data export for a given project"""
    act_dir = make_project_data_dir_name(
        project_uuid=project_uuid,
        data_prefix=data_prefix,
    )
    act_path = os.path.join(root_path, act_dir)
    return act_path


def make_project_data_csv_dir_path(
    project_uuid,
    data_prefix=PROJECT_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Makes a directory path for a (structured) data export for a given project"""
    act_dir = make_project_data_dir_path(
        project_uuid=project_uuid,
        data_prefix=data_prefix,
        root_path=root_path,
    )
    act_path = os.path.join(act_dir, "csv_files")
    return act_path


def make_project_data_json_dir_path(
    project_uuid,
    data_prefix=PROJECT_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Makes a directory path for a (structured) data export for a given project"""
    act_dir = make_project_data_dir_path(
        project_uuid=project_uuid,
        data_prefix=data_prefix,
        root_path=root_path,
    )
    act_path = os.path.join(act_dir, "json_files")
    return act_path


def make_project_data_csv_model_export_path(
    model_db_table,
    act_path=None,
    project_uuid=None,
    data_prefix=PROJECT_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Makes a directory path for a (structured) data export for a given project"""
    if not act_path and project_uuid:
        act_path = make_project_data_csv_dir_path(
            project_uuid=project_uuid,
            data_prefix=data_prefix,
            root_path=root_path,
        )
    os.makedirs(act_path, exist_ok=True)
    csv_file_path = os.path.join(act_path, f'{model_db_table}.csv')
    return csv_file_path


def count_files(directory):
    count = 0
    for root, _, files in os.walk(directory):
        count += len(files)
    return count


def zip_directory(act_path,  zip_path):
    """Create a ZipFile object in write mode and add files to it"""
    print(f'Compress files to {zip_path} from {act_path}')
    file_count = count_files(act_path)
    if not file_count:
        print(f'No files to compress in {act_path}')
        return None
    i = 0
    with ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(act_path):
            for file in files:
                i += 1
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, act_path)
                zipf.write(file_path, arcname=arcname)
                print(f'Compressed {file} ({i} of {file_count})', end="\r",)
    print('\n')
    print(f'FINISHED compressing {file_count} files')


def zip_structured_data_files(
    project_uuid=None,
    data_prefix=PROJECT_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Crete a zip file of project exported CSV files and another zip file of JSON files"""
    act_path = make_project_data_dir_path(
        project_uuid=project_uuid,
        data_prefix=data_prefix,
        root_path=root_path,
    )
    csv_path = make_project_data_csv_dir_path(
        project_uuid=project_uuid,
        data_prefix=data_prefix,
        root_path=root_path,
    )
    json_path = make_project_data_json_dir_path(
        project_uuid=project_uuid,
        data_prefix=data_prefix,
        root_path=root_path,
    )
    csv_zip_path = os.path.join(act_path, 'csv_files.zip')
    json_zip_path = os.path.join(act_path, 'json_files.zip')
    zip_directory(csv_path, csv_zip_path)
    zip_directory(json_path, json_zip_path)


def make_table_data_dir_name(
    table_uuid,
    data_prefix=TABLE_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
):
    """Makes a directory name for a data export of a given table item"""
    return f'{data_prefix}---{table_uuid}'


def make_table_data_dir_path(
    table_uuid,
    data_prefix=TABLE_DATA_ARCHIVE_LOCAL_DIR_PREFIX,
    root_path=ARCHIVE_LOCAL_ROOT_PATH,
):
    """Makes a directory path for a (structured) data export for a given project"""
    act_dir = make_table_data_dir_name(
        table_uuid=table_uuid,
        data_prefix=data_prefix,
    )
    act_path = os.path.join(root_path, act_dir)
    return act_path