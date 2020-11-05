from __future__ import print_function

import sys
import subprocess
import time
import os.path
import pickle
from pprint import pprint

import magic
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

mime = magic.Magic(mime=True)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

FOLDER_NAME = '_MEDIA_DUMPER'
ALLOWED_FILE_TYPES = ['mp4','mp3','cr2','jpg']

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
                mounting_point = stdout[stdout.index('/media'):].strip() + '/DCIM/'
                if os.path.isdir(mounting_point):
                    usb_mounting_point = mounting_point
                    break
        elif sys.platform.startswith('cygwin'):
            # windows
            # wmic logicaldisk get caption
            # and see the default ones such as C or D
            # then ls E:\\ and check for DCIM folder
            continue
        time.sleep(1)

    print('usb found!')
    return usb_mounting_point

def main():

    # detect usb thumb drive
    usb_device = detect_usb_storage()

    listOfFiles = list()
    for (dirpath, dirnames, filenames) in os.walk(usb_device):
        parent_dir = dirpath.replace(usb_device, '')
        parent_dir_id = None
        for filename in filenames:
            # error cannot reverse and get... FUCK
            if filename.split('.').reverse()[0].lower() in ALLOWED_FILE_TYPES:
                # create parent dir 
                gdrive_upload_file(filename, dirpath + '/' + filename)

    # list all dirs inside DCIM
    # if these dirs contains media files
    # get file list
    # create a new folder on drive
    # and start uploading




    # check if there is DCIM folder
    # get files from it and upload them
    return

# def gdrive_create_dir(dirname, parent):


def gdrive_upload_file(file_name, file_location):
    # authenticate and create a service
    service = build('drive', 'v3', credentials=authenticate())

    # check if the folder already exists and get the ID
    folders_res = service.files().list(
        q=f"mimeType = 'application/vnd.google-apps.folder' and name = '{FOLDER_NAME}'", fields='nextPageToken, files(id, name)').execute()
    folder_id = None
    if len(folders_res.get('files', [])):
        folder_id = folders_res.get('files', [])[0]['id']
    # create the folder if it's not existing
    if not folder_id:
        folder_metadata = {
            'name': FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder_id = service.files().create(
            body=folder_metadata, fields='id').execute()['id']
        print('----- MAIN FOLDER CREATED -----')
    else:
        print('----- MAIN FOLDER FOUND -----')

    # upload file
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
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


if __name__ == '__main__':
    main()
