from pprint import pprint
from mendeley_client import *
import os
import unittest
import sys
import time
import datetime
import calendar

class TestEnv:

    mendeley = None
    show_times = True
    sleep_time = 1

    @staticmethod
    def init():
        TestEnv.mendeley = create_client("config_sync.json","sync_keys.pkl")

def main():
    TestEnv.init()
    unittest.main()


def timestamp():
    n = time.gmtime()
    return calendar.timegm(n)

def timed(fn):

    def wrapped(*args, **kwargs):
        now = time.time()
        res = fn(*args, **kwargs)
        delta = time.time()-now
        if TestEnv.show_times:
            print "\n%s took\t%5.3fs"%(fn.__name__,delta)
        return res
    return wrapped

class TestDocumentUpdate(unittest.TestCase):

    # Tests
    def setUp(self):
        self.test_document = TestEnv.mendeley.create_document(document={'type' : 'Book',
                                                                        'title': 'Document creation test', 
                                                                        'year': 2008})
    def tearDown(self):
        TestEnv.mendeley.delete_library_document(self.test_document["document_id"])  

    def update_doc(self, obj):
        document_id = self.test_document["document_id"]
        response = TestEnv.mendeley.update_document(document_id, document=obj)  
        if "error" in response:
            return False, response
        updated_details = TestEnv.mendeley.document_details(document_id)
        return self.compare_documents(updated_details, obj), response

    def update_and_check(self, obj, expected_match):
        match, response = self.update_doc(obj)
        self.assertEqual("error" in response, not expected_match)
        self.assertEqual(match, expected_match)        
    
    def compare_documents(self, docA, docB):
        """Return True if docA[key] == docB[key] for keys in docB
        if docA has extra keys, they are ignored"""

        for key in docB.keys():
            if not key in docA or docA[key] != docB[key]:
                return False
        return True
    
    @timed
    def test_valid_update(self):
        info = {"type":"Book Section",
                "title":"How to kick asses when out of bubble gum",
                "authors":[ {"forename":"Steven", "surname":"Seagal"}, 
                            {"forename":"Dolph","surname":"Lundgren"}],
                "year":"1998"
                }
        self.update_and_check(info, True)

    @timed
    def test_authors_format(self):
        #self.update_and_check({"authors":[ ["Steven", "Seagal"], ["Dolph","Lundgren"]]}, False)
        self.update_and_check({"authors":[ ["Steven Seagal"], ["Dolph Lundgren"]]}, False)
        self.update_and_check({"authors":[ {"forename":"Steven", "surname":"Seagal"}, 
                                           {"forename":"Dolph","surname":"Lundgren"}]}, True)
        self.update_and_check({"authors":"bleh"}, False)
        self.update_and_check({"authors":-1}, False)

    @timed
    def test_invalid_field_type(self):
        # year is a string not a number
        self.update_and_check({"year":1998}, False)

    @timed
    def test_invalid_document_type(self):
        self.update_and_check({"type":"Cat Portrait"}, False)
        
    @timed
    def test_invalid_field(self):
        self.update_and_check({"shoesize":1}, False)

    @timed
    def test_readonly_field(self):
        self.update_and_check({"uuid": "0xdeadb00b5"}, False)
        
class TestDocumentVersion(unittest.TestCase):

    # Utils
    def verify_version(self, obj, expected):
        delta = abs(obj["version"]-expected)
        self.assertTrue(delta < 300)        

    
    # Tests
    def setUp(self):
        self.test_document = TestEnv.mendeley.create_document(document={'type' : 'Book',
                                                                        'title': 'Document creation test', 
                                                                        'year': 2008})
    def tearDown(self):
        TestEnv.mendeley.delete_library_document(self.test_document["document_id"])

    @timed
    def test_version_returned(self):
        """Verify that the version is returned on creation, details and listing"""
        now = timestamp()

        # verify that we get a version number when creating a document
        # at the moment it is the timestamp of creation, so check that it's around
        # the current UTC timestamp (see verify_version)
        created_version = self.test_document["version"]
        self.verify_version(self.test_document, now)

        # verify that the list of documents returns a version and that
        # it matches the version returned earlier
        document_id = self.test_document['document_id']
        documents = TestEnv.mendeley.library()
        self.assertTrue(document_id in documents['document_ids'])

        found_document = None
        for document in documents['documents']:
            if document["id"] == document_id:
                found_document = document
                break
        self.assertTrue(found_document)
        self.assertEqual(found_document["version"], created_version)

        # verify that the document details have the same version
        details = TestEnv.mendeley.document_details(document_id)
        self.assertEqual(details["version"], created_version)

    @timed
    def test_version_on_document_update(self):
        """Verify that an update increases the version number"""
        # sleep a bit to avoid receiving the same timestamp between create and update
        time.sleep(TestEnv.sleep_time)
        current_version = self.test_document["version"]
        response = TestEnv.mendeley.update_document(self.test_document["document_id"], document={"title":"updated title"})
        self.assertTrue("version" in response)
        self.assertTrue(response["version"] > current_version)

    @timed
    def test_version_on_document_folder_update(self):
        # sleep a bit to avoid receiving the same timestamp between create and update
        time.sleep(TestEnv.sleep_time)

        folder = TestEnv.mendeley.create_folder(folder={"name":"test"})
        self.assertTrue("version" in folder)
        current_version = self.test_document["version"]
        response = TestEnv.mendeley.add_document_to_folder(folder["folder_id"], self.test_document["document_id"])

        # verify that the document version changed
        created_version = self.test_document["version"]
        details = TestEnv.mendeley.document_details(self.test_document["document_id"])
        self.assertTrue(details["version"] > created_version)        

        TestEnv.mendeley.delete_folder(folder["folder_id"])


if __name__ == '__main__':
    main()
