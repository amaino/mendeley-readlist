import os
import sys
import unittest

from utils import *
parent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..")
os.sys.path.insert(0, parent_dir) 
from synced_client import *



class TestEnv:
    sclient = None
    debug = True 
    log_file = open("test-sync.log","w")

class TestDocumentsSyncing(unittest.TestCase):

    def log_status(self, message):
        if TestEnv.debug:
            TestEnv.log_file.write("\n#%s\n"%message)
            TestEnv.log_file.write("#"+"-"*len(message)+"\n\n")
            TestEnv.sclient.dump_status(TestEnv.log_file)

    def clear_library(self):
        for doc in TestEnv.sclient.client.library()["document_ids"]:
            TestEnv.sclient.client.delete_library_document(doc)

    def seed_library(self, count):
        ids = []
        for i in range(count):
            response = TestEnv.sclient.client.create_document(document={"type":"Book", "title":"Title %d"%i})
            ids.append(response["document_id"])
        self.assertEqual(len(ids), count)
        return ids

    def document_exists(self, document_id):
        return "error" not in TestEnv.sclient.client.document_details(document_id)
      
    def setUp(self):
        self.clear_library()

    def test_fetch(self):
        count = 5
        ids = self.seed_library(count)
        
        # sync, should have count documents with matching ids
        TestEnv.sclient.sync()
        self.assertEqual(len(TestEnv.sclient.documents), count)
        self.assertEqual(sorted(ids), sorted(TestEnv.sclient.documents.keys()))

        # the status of all documents should be synced
        for document in TestEnv.sclient.documents.values():
            self.assertTrue(document.is_synced())

    def test_local_delete(self):
        count = 5
        ids = self.seed_library(count)
        TestEnv.sclient.sync()

        # locally delete 1 document
        deletion_id = ids[count/2]
        local_document = TestEnv.sclient.documents[deletion_id]
        local_document.delete()
        # the status of the document should be deleted, the count
        # should stay the same until synced
        self.assertTrue(local_document.is_deleted())
        self.assertEqual(len(TestEnv.sclient.documents), count)
        
        # check that the status of the documents are correct
        for docid, document in TestEnv.sclient.documents.items():
            if docid == deletion_id:
                self.assertTrue(document.is_deleted())
            else:
                self.assertTrue(document.is_synced())
        self.log_status("After local delete")

        # sync the deletion
        TestEnv.sclient.sync()
        self.log_status("After sync")
        
        # make sure the document doesn't exist anymore 
        self.assertEqual(len(TestEnv.sclient.documents), count-1)
        self.assertTrue(deletion_id not in TestEnv.sclient.documents.keys())

        # make sure the other documents are unaffected
        for document in TestEnv.sclient.documents.values():
            self.assertTrue(document.is_synced())
            self.assertTrue(document.id() in ids)
            self.assertTrue(document.id() != deletion_id)
        
        # check on the server that the deletion was done
        for doc_id in ids:
            if doc_id == deletion_id:
                self.assertFalse(self.document_exists(doc_id))
            else:
                self.assertTrue(self.document_exists(doc_id))
        
    def test_server_delete(self):
        count = 5 
        ids = self.seed_library(count)
        TestEnv.sclient.sync()

        # delete one doc on the server
        TestEnv.sclient.client.delete_library_document(ids[0])
        self.assertFalse(self.document_exists(ids[0]))

        TestEnv.sclient.sync()
        self.log_status("After sync")
        self.assertEqual(len(TestEnv.sclient.documents), count-1)
        self.assertTrue(ids[0] not in TestEnv.sclient.documents.keys())

        for doc_id in ids[1:]:
            self.assertTrue(doc_id in TestEnv.sclient.documents.keys())
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())
        

    # def test_nop(self):
    #     pass

    # def test_local_update_remote_delete(self):
    #     pass

    # def test_local_update_remote_update_conflict(self):
    #     pass

    def test_local_update_remote_update_no_conflict(self):
        pass

    def test_local_update(self):
        new_title = "updated_title"

        count = 5 
        ids = self.seed_library(count)
        TestEnv.sclient.sync()     

        # change the title of one document
        local_document = TestEnv.sclient.documents[ids[0]]
        local_document.update({"title":new_title})

        original_version = local_document.version()
        
        # the document should be marked as modified
        self.assertTrue(local_document.is_modified())
        for doc_id in ids[1:]:
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())
        
        self.log_status("Before sync")
        TestEnv.sclient.sync()
        self.log_status("After sync")

        # all documents should be synced now
        for doc_id in ids:
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())
            self.assertTrue(self.document_exists(doc_id))

        self.assertEqual(local_document.object.title, new_title)
        self.assertTrue(local_document.version() > original_version)
        
        details = TestEnv.sclient.client.document_details(ids[0])
        self.assertEqual(details["title"], new_title)
        self.assertEqual(details["version"], local_document.version())
        
    def test_remote_update(self):
        new_title = "updated_title"

        count = 5 
        ids = self.seed_library(count)
        TestEnv.sclient.sync()        
        
        local_document = TestEnv.sclient.documents[ids[0]]
        original_version = TestEnv.sclient.documents[ids[0]].version()

        # update the title of a document on the server
        response = TestEnv.sclient.client.update_document(ids[0], document={"title":new_title})
        self.assertTrue("error" not in response)

        # make sure the title was updated on the server
        details = TestEnv.sclient.client.document_details(ids[0])
        self.assertEqual(details["title"], new_title)  
      
        TestEnv.sclient.sync()

        # all documents should be synced
        for doc_id in ids:
            self.assertTrue(TestEnv.sclient.documents[doc_id].is_synced())
            self.assertTrue(self.document_exists(doc_id))       

        self.assertEqual(local_document.object.title, new_title)
        self.assertTrue(local_document.version() > original_version)            

def main(config_file):
    sclient = DummySyncedClient(config_file)

    # verify that the version number is available on this server before running all the tests
    document = TemporaryDocument(sclient.client).document()
    if not "version" in document:
        print "The server doesn't support functionalities required by this test yet"
        sys.exit(1)

    TestEnv.sclient = sclient
    unittest.main()    

if __name__ == "__main__":
    main(get_config_file())
