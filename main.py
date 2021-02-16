from __future__ import print_function

import os.path
import pickle
import subprocess
import sys
import time
from datetime import date
from pprint import pprint

import magic
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

mime = magic.Magic(mime=True)
service = None
main_dir_id = None


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

FOLDER_NAME = '_MEDIA_DUMPER'
ALLOWED_FILE_TYPES = ['mp4', 'mp3', 'cr2', 'jpg', 'arw']
# TODO add constants file
WINDOWS_DRIVES = ['C', 'D']


def main():

    # detect usb thumb drive
    usb_device = detect_usb_storage()

    listOfFiles = list()
    parent_dir = date.today().strftime("%d-%m-%Y")
    parent_dir_id = None
    for (dirpath, dirnames, filenames) in os.walk(usb_device):
        parent_sub_dir = dirpath.replace(usb_device, '')
        parent_sub_dir_id = None
        for filename in filenames:
            # error cannot reverse and get... FUCK
            file_ext = filename.split('.')[::-1][0].lower()
            if file_ext in ALLOWED_FILE_TYPES:
                # create parent dir
                if not parent_dir_id:
                    parent_dir_id = gdrive_create_dir(parent_dir)
                if parent_sub_dir != '' and not parent_sub_dir_id:
                    parent_sub_dir_id = gdrive_create_dir(
                        parent_sub_dir, parent_dir_id)
                gdrive_upload_file(filename, dirpath + '/' +
                                   filename, parent_sub_dir_id if parent_sub_dir_id else parent_dir_id)

    # list all dirs inside DCIM
    # if these dirs contains media files
    # get file list
    # create a new folder on drive
    # and start uploading

    # check if there is DCIM folder
    # get files from it and upload them
    return


def gdrive_create_dir(dirname, parent_id=None):
    '''
    creates a folder on Google Drive
    dirname: name of the folder
    parent_id: id of the parent folder
    returns the id of the created folder
    '''
    service = get_gdrive_service()

    if not parent_id:
        parent_id = gdrive_get_main_dir_id()

    folder_metadata = {
        'name': dirname,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    dir_id = service.files().create(
        body=folder_metadata, fields='id').execute()['id']
    return dir_id


def gdrive_get_main_dir_id():
    '''
    returns the ID of the main folder on Google Drive
    if there's no main folder it gets created
    '''
    global main_dir_id

    if main_dir_id:
        return main_dir_id

    service = get_gdrive_service()
    # check if the folder already exists and get the ID
    folders_res = service.files().list(
        q=f"mimeType = 'application/vnd.google-apps.folder' and name = '{FOLDER_NAME}'", fields='nextPageToken, files(id, name)').execute()
    if len(folders_res.get('files', [])):
        main_dir_id = folders_res.get('files', [])[0]['id']
    # create the folder if it's not existing
    if not main_dir_id:
        folder_metadata = {
            'name': FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        main_dir_id = service.files().create(
            body=folder_metadata, fields='id').execute()['id']
    return main_dir_id


def gdrive_upload_file(file_name, file_location, parent_id):
    service = get_gdrive_service()

    # upload file
    file_metadata = {
        'name': file_name,
        'parents': [parent_id]
    }
    print("START UPLOAD")
    media = MediaFileUpload(file_location,
                            mimetype=mime.from_file(file_location),
                            resumable=True)

    request = service.files().create(body=file_metadata,
                                     media_body=media,
                                     fields='id')
    media.stream()
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print("Uploaded %d%%." % int(status.progress() * 100))
    print("END UPLOAD")


def get_gdrive_service():
    global service
    if not service:
        service = build('drive', 'v3', credentials=authenticate())
    return service


def authenticate():
    creds = None
    print('----- AUTHENTICATING -----')
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    print('----- AUTH COMPLETE -----')
    return creds


def detect_usb_storage():
    print('looking for usb...')
    usb_mounting_point = None
    while not usb_mounting_point:
        if sys.platform.startswith('linux'):
            # linux
            # lsblk -p -o KNAME,MOUNTPOINT | grep dev/sd.*/media (or something like that)
            # get mount point
            # ls $MOUNTPOINT and check for DCIM folder
            process = subprocess.Popen(
                'lsblk -p -o KNAME,MOUNTPOINT | grep dev/sd.*/media',
                shell=True,
                universal_newlines=True,
                stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if len(stdout.strip()):
                mounting_point = stdout[stdout.index(
                    '/media'):].strip() + '/DCIM/'
                if os.path.isdir(mounting_point):
                    usb_mounting_point = mounting_point
                    break
        elif sys.platform.startswith('cygwin') or sys.platform.startswith('win'):
            # windows
            # wmic logicaldisk get caption
            # and see the default ones such as C or D
            # then ls E:\\ and check for DCIM folder
            process = subprocess.Popen(
                'wmic logicaldisk get caption',
                shell=True,
                universal_newlines=True,
                stdout=subprocess.PIPE)
            stdout, stderr = process.communicate()
            mounting_points = stdout.strip().replace(
                'Caption', '').replace(':', '').split()
            if len(mounting_points) > 1:
                # normally on windows C: and D: are hard drive mounting points
                # I'll probably have to ignore them
                for mounting_point in mounting_points:
                    if mounting_point not in WINDOWS_DRIVES:
                        # usb found
                        # search for DCIM folder
                        print(mounting_point + ':\\\\DCIM\\')
                        if os.path.isdir(mounting_point + ':\\\\DCIM\\'):
                            usb_mounting_point = mounting_point + ':\\\\DCIM\\'

        time.sleep(1)

    print('usb found!')
    return usb_mounting_point


if __name__ == '__main__':
    main()
