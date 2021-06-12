"""
This script will set all the paths that the system will use
用来设置框架下所有的关键路径
"""
import os
import json
from collections import OrderedDict

__PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))  # obtain project root path automatically


def if_not_create(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def if_exist_recreate(path):
    if os.path.exists(path):
        os.removedirs(path)
    os.makedirs(path)
    return path


def path_exists(path):
    assert os.path.exists(path) and os.path.isdir(path), '[PATH NOT EXISTS] ' + path
    return path


def file_exists(path):
    assert os.path.exists(path) and os.path.isfile(path), '[FILE NOT EXISTS] ' + path
    return path


def join_paths(root, folders):
    assert isinstance(folders, (list, tuple)), 'Floders must be in a list or tuple, but we got %s' % type(folders)
    for f in folders:
        root = os.path.join(root, f)
    return root


def join_paths_validate(root, folders: list):
    root = join_paths(root, folders)
    if os.path.exists(root):
        return True, root
    return False, root


def get_configs_ordered(config_file):
    with open(config_file) as f:
        cf = json.load(f, object_pairs_hook=OrderedDict)
    return cf


def get_configs(config_file):
    with open(config_file) as f:
        cf = json.load(f)
    return cf


# Common paths
ROOT = __PROJECT_ROOT                                 # rename it for easy way
CONFIGS_DIR = path_exists(os.path.join(ROOT, 'configs'))
LOGS_DIR = if_not_create(os.path.join(ROOT, 'logs'))

# Logger file
LOGGER_CONFIG_FILE = file_exists(os.path.join(CONFIGS_DIR, 'logger.json'))


# yaml file
DATASET_CONFIG_FILE = file_exists(os.path.join(CONFIGS_DIR, 'dataset.yaml'))
VIDEOPLAYER_CONFIG_FILE = file_exists(os.path.join(CONFIGS_DIR, 'videoplayer.yaml'))
ABSCREATOR_CONFIG_FILE = file_exists(os.path.join(CONFIGS_DIR, 'abscreator.yaml'))
