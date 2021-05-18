import os
import unittest
from elifecleaner import parse
from tests.helpers import delete_files_in_folder


class TestParse(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_check_ejp_zip(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        self.assertTrue(parse.check_ejp_zip(zip_file, self.temp_dir))
