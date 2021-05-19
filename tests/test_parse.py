import os
import unittest
from elifecleaner import parse, zip_lib
from tests.helpers import delete_files_in_folder


class TestParse(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_check_ejp_zip(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        self.assertTrue(parse.check_ejp_zip(zip_file, self.temp_dir))

    def test_article_xml_name(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        asset_file_name_map = zip_lib.unzip_zip(zip_file, self.temp_dir)
        expected = (
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
            "tests/tmp/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
        )
        xml_asset = parse.article_xml_asset(asset_file_name_map)
        self.assertEqual(xml_asset, expected)
