import unittest
from collections import OrderedDict
from elifecleaner import zip_lib
from tests.helpers import delete_files_in_folder, read_fixture


class TestZipLib(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_unzip_zip(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        asset_file_name_map = zip_lib.unzip_zip(zip_file, self.temp_dir)
        expected = read_fixture("asset_file_name_map_45644.py")
        self.assertEqual(asset_file_name_map, expected)
