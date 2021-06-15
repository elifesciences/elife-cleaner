import os
import unittest
from mock import patch
from xml.etree import ElementTree
import wand
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

    @patch.object(wand.image.Image, "allocate")
    def test_pdf_page_count_wand_runtime_error(self, mock_image_allocate):
        mock_image_allocate.side_effect = wand.exceptions.WandRuntimeError()
        zip_lib.unzip_zip(
            "tests/test_data/30-01-2019-RA-eLife-45644.zip", self.temp_dir
        )
        pdf_path = "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf"
        with self.assertRaises(wand.exceptions.WandRuntimeError):
            self.assertIsNone(parse.pdf_page_count(pdf_path))
        with open(self.log_file, "r") as open_file:
            self.assertEqual(
                open_file.readline(),
                (
                    "ERROR elifecleaner:parse:pdf_page_count: "
                    "WandRuntimeError in pdf_page_count(), imagemagick may not be installed\n"
                ),
            )

    @patch.object(wand.image.Image, "allocate")
    def test_pdf_page_count_wand_policy_error(self, mock_image_allocate):
        mock_image_allocate.side_effect = wand.exceptions.PolicyError()
        zip_lib.unzip_zip(
            "tests/test_data/30-01-2019-RA-eLife-45644.zip", self.temp_dir
        )
        pdf_path = "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf"
        with self.assertRaises(wand.exceptions.PolicyError):
            self.assertIsNone(parse.pdf_page_count(pdf_path))
        with open(self.log_file, "r") as open_file:
            self.assertEqual(
                open_file.readline(),
                (
                    "ERROR elifecleaner:parse:pdf_page_count: "
                    "PolicyError in pdf_page_count(), "
                    "imagemagick policy.xml may not allow reading PDF files\n"
                ),
            )


class TestParseArticleXML(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_parse_article_xml(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write("<article/>")
        root = parse.parse_article_xml(xml_file_path)
        self.assertIsNotNone(root)

    def test_parse_article_xml_entities(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write("<article>&mdash;&lt;&gt;&amp;&quot;&beta;</article>")
        expected = b'<article>&#8212;&lt;&gt;&amp;"&#946;</article>'
        root = parse.parse_article_xml(xml_file_path)
        self.assertIsNotNone(root)
        self.assertEqual(ElementTree.tostring(root), expected)

    def test_parse_article_xml_failure(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write("malformed xml")
        with self.assertRaises(ElementTree.ParseError):
            parse.parse_article_xml(xml_file_path)


class TestRepairArticleXml(unittest.TestCase):
    def test_malformed_xml(self):
        xml_string = "malformed xml"
        expected = "malformed xml"
        self.assertEqual(parse.repair_article_xml(xml_string), expected)

    def test_research_article(self):
        xml_string = '<article article-type="research-article"></article>'
        expected = (
            '<article article-type="research-article" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"></article>'
        )
        self.assertEqual(parse.repair_article_xml(xml_string), expected)

    def test_article_commentary(self):
        xml_string = '<article article-type="article-commentary"></article>'
        expected = (
            '<article article-type="article-commentary" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"></article>'
        )
        self.assertEqual(parse.repair_article_xml(xml_string), expected)

    def test_article_tag(self):
        xml_string = "<article></article>"
        expected = '<article xmlns:xlink="http://www.w3.org/1999/xlink"></article>'
        self.assertEqual(parse.repair_article_xml(xml_string), expected)

    def test_xlink_namespace_already_exists(self):
        xml_string = '<article xmlns:xlink="http://www.w3.org/1999/xlink"></article>'
        expected = '<article xmlns:xlink="http://www.w3.org/1999/xlink"></article>'
        self.assertEqual(parse.repair_article_xml(xml_string), expected)
