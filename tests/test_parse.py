import os
import unittest
from xml.etree import ElementTree
from elifecleaner import configure_logging, parse, zip_lib
from tests.helpers import delete_files_in_folder, read_fixture


class TestParse(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        configure_logging(self.log_file)

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_check_ejp_zip(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        warning_prefix = (
            "WARNING elifecleaner:parse:check_ejp_zip: multiple page PDF figure file:"
        )
        expected = [
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf\n" % warning_prefix,
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf\n" % warning_prefix,
        ]
        result = parse.check_ejp_zip(zip_file, self.temp_dir)
        self.assertTrue(result)
        log_file_lines = []
        with open(self.log_file, "r") as open_file:
            for line in open_file:
                log_file_lines.append(line)
        self.assertEqual(log_file_lines, expected)

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

    def test_file_extension(self):
        self.assertEqual(parse.file_extension("image.JPG"), "jpg")
        self.assertEqual(parse.file_extension("folder/figure.pdf"), "pdf")
        self.assertEqual(parse.file_extension("test"), None)
        self.assertIsNone(parse.file_extension(None))

    def test_pdf_page_count_blank(self):
        self.assertIsNone(parse.pdf_page_count(""))
