import datetime
from dateutil import parser
import os
import subprocess
from django.conf import settings

"""
These functions get updated information from the git log of template (
    or other files
)
"""


GIT_LOG_DATE = f'git -C {settings.BASE_DIR} log -1 --date=iso-local --format="%cd" '


def get_file_git_updated_datetime(file_path):
    """Gets a datetime object for the last git update of a file

    :param str file_path: A file that should have a git history
        log

    return datetime (object) or None
    """
    if not os.path.exists(file_path):
        return None
    dt_format = '%Y-%m-%dT%H:%M:%S'
    commands = [
        'git',
        '-C',
        settings.BASE_DIR,
        'log',
        '-1',
        f'--date=format-local:{dt_format}',
        '--format="%cd"',
        file_path
    ]
    try:
        updated_str = subprocess.check_output(commands)
    except:
        print('command failed')
        command_str = ' '.join(commands)
        print(command_str)
        return None
    date_str = str(updated_str.decode()).strip().replace('"', '')
    dt = datetime.datetime.strptime(date_str, dt_format)
    return dt


def get_template_file_git_updated_datetime(template_path):
    """Gets a datetime object for the last git update of a file in the templates

    :param str template_path: A file within the project's templates
        directory

    return datetime (object) or None
    """
    file_path = os.path.join(
        settings.BASE_DIR,
        'opencontext_py',
        'templates',
        template_path,
    )
    return get_file_git_updated_datetime(file_path)


def get_template_file_git_updated_datetime_str(template_path):
    """Gets a string datetime for the last git update of a file in the templates

    :param str template_path: A file within the project's templates
        directory

    return str datetime or None
    """
    dt = get_template_file_git_updated_datetime(template_path)
    if not dt:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'