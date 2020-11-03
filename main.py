from __future__ import print_function

import os.path
import pickle
from pprint import pprint

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

FOLDER_NAME = '_MEDIA_DUMPER'


def main():
    # authenticate and create a service
    service = build('drive', 'v3', credentials=authenticate())
    # check if the folder already exists and get the ID
    folders_res = service.files().list(q=f"mimeType = 'application/vnd.google-apps.folder' and name = '{FOLDER_NAME}'",
                                       fields='nextPageToken, files(id, name)').execute()
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
        'name': 'todo.txt',
        'parents': [folder_id]
    }
    media = MediaFileUpload('todo.txt',
                            mimetype='text/plain',
                            resumable=True)
    file = service.files().create(body=file_metadata,
                                  media_body=media,
                                  fields='id').execute()
    print('File ID: %s' % file.get('id'))


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
