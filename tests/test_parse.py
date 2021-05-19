import os
import unittest
from collections import OrderedDict
from xml.etree import ElementTree
from elifecleaner import parse, zip_lib
from tests.helpers import delete_files_in_folder, read_fixture


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

    def test_parse_article_xml(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write("<article/>")
        root = parse.parse_article_xml(xml_file_path)
        self.assertIsNotNone(root)

    def test_parse_article_xml_failure(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write("malformed xml")
        with self.assertRaises(ElementTree.ParseError):
            parse.parse_article_xml(xml_file_path)

    def test_file_list(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        asset_file_name_map = zip_lib.unzip_zip(zip_file, self.temp_dir)
        xml_asset = parse.article_xml_asset(asset_file_name_map)
        root = parse.parse_article_xml(xml_asset[1])
        expected = read_fixture("file_list_45644.py")

        files = parse.file_list(root)
        self.assertEqual(files, expected)
