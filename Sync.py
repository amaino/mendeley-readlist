'''
Created on 24 aug 2012

@author: marcuni
'''

from mendeley_client import MendeleyClientConfig, MendeleyClient, MendeleyTokensStore
import os
import sys
import shutil

# Load the configuration file
config = MendeleyClientConfig()
if not config.is_valid():
    print "Please edit config.json before running this script"
    sys.exit(1)

# create a client and load tokens from the pkl file
mendeley = MendeleyClient(config.api_key, config.api_secret)
tokens_store = MendeleyTokensStore()

# configure the client to use a specific token
# if no tokens are available, prompt the user to authenticate
access_token = tokens_store.get_access_token("test_account")
if not access_token:
    mendeley.interactive_auth()
    tokens_store.add_account("test_account",mendeley.get_access_token())
else:
    mendeley.set_access_token(access_token)


documents = mendeley.folder_documents(34240081)['document_ids']

for document_id in documents:
    document = mendeley.document_details(document_id)
    theFile = config.reading_list + '/' + document['title'] + '.pdf'
    theMendeleyFile = config.mendeley_library + '/' + document['year'] + '/' + document['title'] + '.pdf'
    if os.path.exists(theFile):
        if (os.path.getmtime(theFile) < os.path.getmtime(theMendeleyFile)):
            shutil.copy2(theMendeleyFile, theFile)
        elif (os.path.getmtime(theFile) > os.path.getmtime(theMendeleyFile)):
            shutil.copy2(theFile, theMendeleyFile)
    else:
        shutil.copy2(theMendeleyFile, theFile)

