from __future__ import print_function

import os.path
import pickle
from pprint import pprint

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']


def main():
    # authenticate and create a service
    service = build('drive', 'v3', credentials=authenticate())

    # folder_metadata = {
    #     'name': '_MEDIA_DUMPER',
    #     'mimeType': 'application/vnd.google-apps.folder'
    # }
    # res = service.files().create(body=folder_metadata, fields='id').execute()
    # print(res)
    files_list = service.files().list(q="mimeType = 'application/vnd.google-apps.folder' and name = '_MEDIA_DUMPER'",
                                      fields='nextPageToken, files(id, name)').execute()

    pprint(files_list.get('files', []))


def authenticate():
    creds = None
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
    return creds


if __name__ == '__main__':
    main()
