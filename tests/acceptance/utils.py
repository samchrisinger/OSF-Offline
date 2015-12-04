import  requests
from osfoffline.client.osf import User, Node
import tests.acceptance.settings as settings
import json
from decorator import decorator
import time
import os
import shutil

user = None # todo: authorize client
headers = {'Authorization':'Bearer {}'.format(user.oauth_token)}

session = requests.Session()
session.headers.update(headers)


def create_new_node(title, parent=None):
    """

    :param title: title of new node to create
    :param parent: make new node a child of parent. Can be None
    :return: the id of the new node
    """
    #todo: relate to parent node
    body = {
            "data": {
                "type": "nodes", # required
                "attributes": {
                    "title":    title,         # required
                    "category": 'Project',      # required
                }
            }
    }

    headers['Content-Type']='application/json'
    headers['Accept']='application/json'

    ret = requests.post(Node.get_url(), data=json.dumps(body), headers=headers)
    return ret.json()['data']['id']

nid1 = create_new_node(settings.base_project_name)

@decorator
def repeat_until_success(func, *args, **kwargs):
    """
    Retry the assertion until it becomes true. Keep retrying for settings.REPEAT_TIME

    :param func: an assertion function
    :param args: args given to assertion function
    :param kwargs: kwards given to assertion function

    :raise if the assertion function is ever true, then just end. If the assertion function is returning
     False even after settings.REPEAT_TIME, then raise TestFail

    """
    for i in range(20):
        if func(*args, **kwargs):
            return
        else:
            time.sleep(5)
    raise TestFail


def create_local(*args, file_name=None):
    """
    usage:
        to create a folder: create_local('path','to','folder')
        to create a file:   create_local('path', 'to', 'folder', filename='myfile')
    :param args: folder path
    :param file_name: optionally create a file at this path
    :return: if creating a file, return the contents of the file
    """
    path = build_path(*args)
    if not os.path.exists(path):
        os.makedirs(path)
    if file_name:
        file_path = os.path.join(path, file_name)
        file = open(file_path, 'w+')
        contents = 'some text inside file {}'.format(file_path)
        file.write(contents)
        file.close()
        return contents.encode('utf-8')



def build_path(*args):
    """
    :param args: folder path
    :return:
    """
    return os.path.join(settings.project_path, *args)



class TestFail(Exception):
    pass


def get_node_file_folders(node_id):
    """
    get the file folders given a node id.
    This makes 2 get requests. First for the osfstorage and then for the files/folders inside that.
    Thus it is abstracting out the osfstorage step for us.
    :param node_id:
    :return: [file_folder_as_json]
    """
    node_files_url = Node.get_url(node_id) + 'files/'
    resp = session.get(node_files_url)

    assert resp.ok
    osf_storage_folder = resp.json()['data'][0]
    assert osf_storage_folder['attributes']['name'] == 'osfstorage'
    children_resp = session.get(osf_storage_folder['relationships']['files']['links']['related']['href'])
    assert children_resp.ok
    return [file_folder for file_folder in children_resp.json()['data']]

def get_children_file_folders(parent_folder):
    url = parent_folder['relationships']['files']['links']['related']['href']
    resp = session.get(url)
    assert resp.ok
    return [file_folder for file_folder in resp.json()['data']]

def in_list(name, remote_list, is_dir):
    """
    determine if the given file or folder is in the remote list
    :param name: name of file or folder
    :param remote_list:
    :param is_dir: is the given input a file or folder
    :return:
    """
    file_or_folder = 'folder' if is_dir else 'file'
    for remote in remote_list:
        if remote['type']==file_or_folder and remote['attributes']['name'] == name:
            return True
    return False

def get_from_list(name, remote_list, is_dir):
    """
    get the desired file or folder from the remote list. You only input the file/folder name
    :param name: name of file or folder
    :param remote_list:
    :param is_dir: is the given input a file or folder
    :return:
    """
    file_or_folder = 'folder' if is_dir else 'file'
    for remote in remote_list:
        if remote['type']==file_or_folder and remote['attributes']['name'] == name:
            return remote
    assert FileNotFoundError

# Assertions

@repeat_until_success
def assert_contains_folder(name, nid, parent_folder=None):
    if parent_folder:
        children = get_children_file_folders(parent_folder)
    else:
        children = get_node_file_folders(nid)

    return in_list(name, children, True)

@repeat_until_success
def assert_contains_file(name, contents, nid, parent_folder=None):
    if parent_folder:
        children = get_children_file_folders(parent_folder)
    else:
        children = get_node_file_folders(nid)

    if in_list(name, children, False):
        file = get_from_list(name, children, False)
        resp = session.get(file['links']['download'])
        assert resp.ok
        assert resp.content == contents
        return True
    return False


@repeat_until_success
def assert_file_not_exist(name, nid, parent_folder=None):
        return _assert_file_folder_not_exist(name, nid, False, parent_folder)

@repeat_until_success
def assert_folder_not_exist(name, nid, parent_folder=None):
    return _assert_file_folder_not_exist(name, nid, True, parent_folder)

def _assert_file_folder_not_exist(name, nid, is_folder, parent_folder):
    if parent_folder:
        children = get_children_file_folders(parent_folder)
    else:
        children = get_node_file_folders(nid)
    return not in_list(name, children, is_folder)



def get_remote(name, nid, is_dir, parent=None):
    if parent:
        children = get_children_file_folders(parent)
    else:
        children = get_node_file_folders(nid)

    file_or_folder = 'folder' if is_dir else 'file'
    for child in children:
        if child['type']==file_or_folder and child['attributes']['name'] == name:
            return child
    raise FileNotFoundError



def delete_all_local():
    for file_folder in os.listdir(settings.project_path):
        path = os.path.join(settings.project_path, file_folder)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

@repeat_until_success
def assert_node_has_no_file_folders(nid):
    file_folders = get_node_file_folders(nid)
    return len(file_folders)==0

@repeat_until_success
def assert_local_has_components_folder():
    return os.path.isdir(build_path('Components'))

def assert_contains_project():
    if not os.path.isdir(settings.project_path):
        assert TestFail
