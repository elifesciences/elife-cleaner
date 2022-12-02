import os
import unittest
import zipfile
from collections import OrderedDict
from xml.etree import ElementTree
from mock import patch
import wand
from elifecleaner import LOGGER, configure_logging, parse, pdf_utils, zip_lib
from elifecleaner.utils import CONTROL_CHARACTER_ENTITY_REPLACEMENT
from tests.helpers import delete_files_in_folder, read_fixture, read_log_file_lines


class TestParse(unittest.TestCase):
    def test_file_extension(self):
        self.assertEqual(parse.file_extension("image.JPG"), "jpg")
        self.assertEqual(parse.file_extension("folder/figure.pdf"), "pdf")
        self.assertEqual(parse.file_extension("test"), None)
        self.assertIsNone(parse.file_extension(None))

    def test_pdf_page_count_blank(self):
        self.assertIsNone(parse.pdf_page_count(""))


class TestCheckEjpZip(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.original_repair_xml_value = parse.REPAIR_XML

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])
        parse.REPAIR_XML = self.original_repair_xml_value

    @patch.object(parse, "check_art_file")
    @patch.object(pdf_utils, "pdf_image_pages")
    @patch.object(pdf_utils, "pdfimages_exists")
    def test_check_ejp_zip(
        self, mock_pdfimages_exists, mock_pdf_image_pages, fake_check_art_file
    ):
        fake_check_art_file.return_value = True
        mock_pdfimages_exists.return_value = True
        mock_pdf_image_pages.return_value = {1, 2}
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        zip_file_name = zip_file.split(os.sep)[-1]
        log_prefix = (
            "elifecleaner:parse:check_multi_page_figure_pdf: %s"
        ) % zip_file_name
        warning_prefix = ("WARNING %s multiple page PDF figure file:") % log_prefix
        info_prefix = ("INFO %s using pdfimages to check PDF figure file:") % log_prefix
        info_pages_prefix = (
            "INFO %s pdfimages found images on pages {1, 2} in PDF figure file:"
        ) % log_prefix
        expected = [
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf\n" % info_prefix,
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf\n"
            % info_pages_prefix,
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf\n" % warning_prefix,
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf\n" % info_prefix,
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf\n"
            % info_pages_prefix,
            "%s 30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf\n" % warning_prefix,
        ]
        result = parse.check_ejp_zip(zip_file, self.temp_dir)
        self.assertTrue(result)
        self.assertEqual(read_log_file_lines(self.log_file), expected)

    def test_check_ejp_zip_do_not_repair_xml(self):
        parse.REPAIR_XML = False
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        with self.assertRaises(ElementTree.ParseError):
            parse.check_ejp_zip(zip_file, self.temp_dir)
        log_file_lines = read_log_file_lines(self.log_file)
        self.assertTrue(log_file_lines[0].startswith("ERROR"))

    @patch.object(parse, "check_art_file")
    def test_check_ejp_zip_missing_file(self, fake_check_art_file):
        fake_check_art_file.return_value = True
        zip_file = "tests/test_data/08-11-2020-FA-eLife-64719.zip"
        # remove a file from a copy of the zip file for testing
        test_zip_file_name = os.path.join(self.temp_dir, "test_missing_file.zip")
        zip_file_name = test_zip_file_name.split(os.sep)[-1]

        remove_files = ["08-11-2020-FA-eLife-64719/eLife64719_figure2_classB.png"]
        with zipfile.ZipFile(zip_file, "r") as input_zipfile:
            with zipfile.ZipFile(test_zip_file_name, "w") as output_zipfile:
                for zip_info in input_zipfile.infolist():
                    if zip_info.filename not in remove_files:
                        output_zipfile.writestr(
                            zip_info, input_zipfile.read(zip_info.filename)
                        )

        warning_prefix = (
            "WARNING elifecleaner:parse:check_missing_files: %s" % zip_file_name
        )
        missing_file_prefix = "does not contain a file in the manifest:"
        expected = [
            "%s %s eLife64719_figure2_classB.png\n"
            % (warning_prefix, missing_file_prefix),
        ]

        result = parse.check_ejp_zip(test_zip_file_name, self.temp_dir)
        self.assertTrue(result)
        self.assertEqual(read_log_file_lines(self.log_file), expected)

    @patch.object(parse, "check_art_file")
    def test_check_ejp_zip_extra_file(self, fake_check_art_file):
        fake_check_art_file.return_value = True
        zip_file = "tests/test_data/08-11-2020-FA-eLife-64719.zip"
        # alter the manifest XML in the zip file for testing
        test_zip_file_name = os.path.join(self.temp_dir, "test_missing_file.zip")
        zip_file_name = test_zip_file_name.split(os.sep)[-1]

        xml_file_name = "08-11-2020-FA-eLife-64719/08-11-2020-FA-eLife-64719.xml"

        with zipfile.ZipFile(zip_file, "r") as input_zipfile:
            with zipfile.ZipFile(test_zip_file_name, "w") as output_zipfile:
                for zip_info in input_zipfile.infolist():
                    if zip_info.filename == xml_file_name:
                        # replace <file> tags with <file_dummy> tags in the manifest XML
                        mainfest_xml = input_zipfile.read(zip_info.filename)
                        mainfest_xml = mainfest_xml.replace(
                            b"<file", b"<file_dummy"
                        ).replace(b"</file", b"</file_dummy")
                        output_zipfile.writestr(zip_info, mainfest_xml)
                    else:
                        output_zipfile.writestr(
                            zip_info, input_zipfile.read(zip_info.filename)
                        )

        warning_prefix = (
            "WARNING elifecleaner:parse:check_extra_files: %s" % zip_file_name
        )
        extra_file_prefix = "has file not listed in the manifest:"
        expected = [
            "%s %s 08-11-2020-FA-eLife-64719.pdf\n"
            % (warning_prefix, extra_file_prefix),
            "%s %s eLife64719_figure1_classB.png\n"
            % (warning_prefix, extra_file_prefix),
            "%s %s eLife64719_figure2_classB.png\n"
            % (warning_prefix, extra_file_prefix),
            "%s %s eLife64719_template5.docx\n" % (warning_prefix, extra_file_prefix),
        ]

        result = parse.check_ejp_zip(test_zip_file_name, self.temp_dir)
        self.assertTrue(result)
        self.assertEqual(read_log_file_lines(self.log_file), expected)

    @patch.object(parse, "check_art_file")
    def test_check_ejp_zip_missing_file_by_name(self, fake_check_art_file):
        fake_check_art_file.return_value = True
        zip_file = "tests/test_data/08-11-2020-FA-eLife-64719.zip"
        # alter the manifest XML in the zip file for testing
        test_zip_file_name = os.path.join(self.temp_dir, "test_missing_file.zip")
        zip_file_name = test_zip_file_name.split(os.sep)[-1]

        xml_file_name = "08-11-2020-FA-eLife-64719/08-11-2020-FA-eLife-64719.xml"

        with zipfile.ZipFile(zip_file, "r") as input_zipfile:
            with zipfile.ZipFile(test_zip_file_name, "w") as output_zipfile:
                for zip_info in input_zipfile.infolist():
                    if zip_info.filename == xml_file_name:
                        # replace <file> tags with <file_dummy> tags in the manifest XML
                        mainfest_xml = input_zipfile.read(zip_info.filename)
                        mainfest_xml = mainfest_xml.replace(
                            b"<meta-value>Figure 2</meta-value>",
                            b"<meta-value>Figure 3</meta-value>",
                        )
                        output_zipfile.writestr(zip_info, mainfest_xml)
                    else:
                        output_zipfile.writestr(
                            zip_info, input_zipfile.read(zip_info.filename)
                        )

        warning_prefix = (
            "WARNING elifecleaner:parse:check_missing_files_by_name: %s" % zip_file_name
        )
        extra_file_prefix = "has file missing from expected numeric sequence:"
        expected = [
            "%s %s Figure 2\n" % (warning_prefix, extra_file_prefix),
        ]

        result = parse.check_ejp_zip(test_zip_file_name, self.temp_dir)
        self.assertTrue(result)
        self.assertEqual(read_log_file_lines(self.log_file), expected)


class TestArticleXmlAsset(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_article_xml_name(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        asset_file_name_map = zip_lib.unzip_zip(zip_file, self.temp_dir)
        expected = (
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
            "tests/tmp/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
        )
        xml_asset = parse.article_xml_asset(asset_file_name_map)
        self.assertEqual(xml_asset, expected)

    def test_article_xml_name_empty(self):
        asset_file_name_map = []
        expected = None
        xml_asset = parse.article_xml_asset(asset_file_name_map)
        self.assertEqual(xml_asset, expected)


class TestPdfPageCount(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    @patch.object(wand.image.Image, "allocate")
    def test_pdf_page_count_wand_runtime_error(self, mock_image_allocate):
        mock_image_allocate.side_effect = wand.exceptions.WandRuntimeError()
        zip_lib.unzip_zip(
            "tests/test_data/30-01-2019-RA-eLife-45644.zip", self.temp_dir
        )
        pdf_path = "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf"
        with self.assertRaises(wand.exceptions.WandRuntimeError):
            self.assertIsNone(parse.pdf_page_count(pdf_path))
        expected = (
            "ERROR elifecleaner:parse:pdf_page_count: "
            "WandRuntimeError in pdf_page_count(), imagemagick may not be installed\n"
        )
        log_file_lines = read_log_file_lines(self.log_file)
        self.assertEqual(log_file_lines[0], expected)

    @patch.object(wand.image.Image, "allocate")
    def test_pdf_page_count_wand_policy_error(self, mock_image_allocate):
        mock_image_allocate.side_effect = wand.exceptions.PolicyError()
        zip_lib.unzip_zip(
            "tests/test_data/30-01-2019-RA-eLife-45644.zip", self.temp_dir
        )
        pdf_path = "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf"
        with self.assertRaises(wand.exceptions.PolicyError):
            self.assertIsNone(parse.pdf_page_count(pdf_path))
        expected = (
            "ERROR elifecleaner:parse:pdf_page_count: "
            "PolicyError in pdf_page_count(), "
            "imagemagick policy.xml may not allow reading PDF files\n"
        )
        log_file_lines = read_log_file_lines(self.log_file)
        self.assertEqual(log_file_lines[0], expected)


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

    def test_parse_article_xml_control_character_entities(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write(
                "<article><title>To &#x001D;nd odd entities.</title></article>"
            )
        expected = b"<article><title>To %snd odd entities.</title></article>" % bytes(
            CONTROL_CHARACTER_ENTITY_REPLACEMENT, encoding="utf-8"
        )
        root = parse.parse_article_xml(xml_file_path)
        self.assertIsNotNone(root)
        self.assertEqual(ElementTree.tostring(root), expected)

    def test_parse_article_xml_control_characters(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write(
                "<article><title>To %snd odd entities.</title></article>" % chr(29)
            )
        expected = b"<article><title>To %snd odd entities.</title></article>" % bytes(
            CONTROL_CHARACTER_ENTITY_REPLACEMENT, encoding="utf-8"
        )
        root = parse.parse_article_xml(xml_file_path)
        self.assertIsNotNone(root)
        self.assertEqual(ElementTree.tostring(root), expected)

    def test_parse_article_xml_ampersand(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        xml_string_pattern = "<article>And %s And &amp; &#8220;And&#8221;</article>"
        with open(xml_file_path, "w") as open_file:
            open_file.write(xml_string_pattern % "&")
        expected = bytes(xml_string_pattern % "&amp;", encoding="utf-8")
        root = parse.parse_article_xml(xml_file_path)
        self.assertIsNotNone(root)
        self.assertEqual(ElementTree.tostring(root), expected)

    def test_parse_article_xml_failure(self):
        xml_file_path = os.path.join(self.temp_dir, "test.xml")
        with open(xml_file_path, "w") as open_file:
            open_file.write("malformed xml")
        with self.assertRaises(ElementTree.ParseError):
            parse.parse_article_xml(xml_file_path)


class TestParseXML(unittest.TestCase):
    def setUp(self):
        xml_string = """<article>
<front>
  <journal-meta>
    <journal-id journal-id-type="foo">bar</journal-id>
    <journal-title-group>
      <journal-title>eLife</journal-title>
    </journal-title-group>
    <publisher>
        <publisher-name>eLife Sciences Publications, Ltd</publisher-name>
    </publisher>
  </journal-meta>
</front>
</article>"""
        self.root = ElementTree.fromstring(xml_string)

    def test_xml_journal_id_values(self):
        id_values = parse.xml_journal_id_values(self.root)
        self.assertEqual(id_values, {"foo": "bar"})

    def test_xml_journal_id_values_none(self):
        id_values = parse.xml_journal_id_values(ElementTree.fromstring("<article/>"))
        self.assertEqual(id_values, {})

    def test_xml_journal_title(self):
        title = parse.xml_journal_title(self.root)
        self.assertEqual(title, "eLife")

    def test_xml_journal_title_none(self):
        title = parse.xml_journal_title(ElementTree.fromstring("<article/>"))
        self.assertEqual(title, None)

    def test_xml_publisher_name(self):
        name = parse.xml_publisher_name(self.root)
        self.assertEqual(name, "eLife Sciences Publications, Ltd")

    def test_xml_publisher_name_none(self):
        name = parse.xml_publisher_name(ElementTree.fromstring("<article/>"))
        self.assertEqual(name, None)


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

    def test_artice_id_tag(self):
        # do not add to <article-id> tags
        xml_string = (
            '<article article-type="research-article"></article>'
            '<article-id pub-id-type="publisher-id">45644</article-id>'
        )
        expected = (
            '<article article-type="research-article" xmlns:xlink="http://www.w3.org/1999/xlink">'
            '</article><article-id pub-id-type="publisher-id">45644</article-id>'
        )
        self.assertEqual(parse.repair_article_xml(xml_string), expected)


class TestParseFileList(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_file_list(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        asset_file_name_map = zip_lib.unzip_zip(zip_file, self.temp_dir)
        xml_asset = parse.article_xml_asset(asset_file_name_map)
        root = parse.parse_article_xml(xml_asset[1])
        expected = read_fixture("file_list_45644.py")

        files = parse.file_list(root)
        self.assertEqual(files, expected)


class TestCheckMissingFiles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    @patch.object(parse, "find_missing_files")
    def test_check_missing_files(self, mock_missing_files):
        identifier = "test.zip"
        missing_files = ["file.jpg"]
        mock_missing_files.return_value = missing_files
        expected = [
            (
                "WARNING elifecleaner:parse:check_missing_files: %s "
                "does not contain a file in the manifest: %s\n"
            )
            % (identifier, missing_files[0])
        ]
        parse.check_missing_files([], {}, identifier)
        self.assertEqual(read_log_file_lines(self.log_file), expected)


class TestFindMissingFiles(unittest.TestCase):
    def test_find_missing_files_complete(self):
        files = []
        asset_file_name_map = {}
        expected = []
        self.assertEqual(parse.find_missing_files(files, asset_file_name_map), expected)

    def test_find_missing_files_incomplete(self):
        files = [
            OrderedDict(
                [
                    ("file_type", "figure"),
                    ("id", "2063134"),
                    ("upload_file_nm", "eLife64719_figure1_classB.png"),
                    (
                        "custom_meta",
                        [
                            OrderedDict(
                                [
                                    ("meta_name", "Figure number"),
                                    ("meta_value", "Figure 1"),
                                ]
                            )
                        ],
                    ),
                ]
            )
        ]
        asset_file_name_map = {}
        expected = ["eLife64719_figure1_classB.png"]
        self.assertEqual(parse.find_missing_files(files, asset_file_name_map), expected)


class TestCheckMultiPageFigurePdf(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    @patch.object(pdf_utils, "pdf_image_pages")
    @patch.object(pdf_utils, "pdfimages_exists")
    def test_check_multi_page_figure_pdf(
        self, mock_pdfimages_exists, mock_pdf_image_pages
    ):
        figures = [{"file_name": "figure.pdf", "pages": 2}]
        zip_file = "30-01-2019-RA-eLife-45644.zip"
        mock_pdfimages_exists.return_value = False
        mock_pdf_image_pages.return_value = {1, 2}
        expected = None
        self.assertEqual(parse.check_multi_page_figure_pdf(figures, zip_file), expected)
        log_file_lines = read_log_file_lines(self.log_file)
        self.assertTrue(
            "multiple page PDF figure file: figure.pdf" in log_file_lines[0]
        )

    @patch.object(pdf_utils, "pdf_image_pages")
    @patch.object(pdf_utils, "pdfimages_exists")
    def test_check_multi_page_figure_pdf_exception(
        self, mock_pdfimages_exists, mock_pdf_image_pages
    ):
        figures = [{"file_name": "figure.pdf", "pages": 2}]
        zip_file = "30-01-2019-RA-eLife-45644.zip"
        mock_pdfimages_exists.return_value = True
        mock_pdf_image_pages.side_effect = Exception("An exception")
        expected = None
        self.assertEqual(parse.check_multi_page_figure_pdf(figures, zip_file), expected)
        log_file_lines = read_log_file_lines(self.log_file)
        self.assertTrue("Exception:" in log_file_lines[-2])
        self.assertTrue(
            "multiple page PDF figure file: figure.pdf" in log_file_lines[-1]
        )


class TestCheckExtraFiles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    @patch.object(parse, "find_extra_files")
    def test_check_extra_files(self, mock_extra_files):
        identifier = "test.zip"
        extra_files = ["file.jpg"]
        mock_extra_files.return_value = extra_files
        expected = [
            (
                "WARNING elifecleaner:parse:check_extra_files: %s "
                "has file not listed in the manifest: %s\n"
            )
            % (identifier, extra_files[0])
        ]
        parse.check_extra_files([], {}, identifier)
        self.assertEqual(read_log_file_lines(self.log_file), expected)


class TestFindExtraFiles(unittest.TestCase):
    def test_find_extra_files_empty(self):
        files = []
        asset_file_name_map = {}
        expected = []
        self.assertEqual(parse.find_extra_files(files, asset_file_name_map), expected)

    def test_find_extra_files_complete(self):
        files = [
            OrderedDict(
                [
                    ("file_type", "figure"),
                    ("id", "2063134"),
                    ("upload_file_nm", "eLife64719_figure1_classB.png"),
                    ("custom_meta", []),
                ]
            )
        ]
        asset_file_name_map = {
            "08-11-2020-FA-eLife-64719/eLife64719_figure1_classB.png": (
                "tests/tmp/08-11-2020-FA-eLife-64719/eLife64719_figure1_classB.png"
            )
        }
        expected = []
        self.assertEqual(parse.find_extra_files(files, asset_file_name_map), expected)

    def test_find_extra_files_extra(self):
        files = []
        asset_file_name_map = {
            "08-11-2020-FA-eLife-64719/eLife64719_figure1_classB.png": (
                "tests/tmp/08-11-2020-FA-eLife-64719/eLife64719_figure1_classB.png"
            )
        }
        expected = ["eLife64719_figure1_classB.png"]
        self.assertEqual(parse.find_extra_files(files, asset_file_name_map), expected)


class TestCheckMissingFilesByName(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    @patch.object(parse, "find_missing_files_by_name")
    def test_check_missing_files_by_name(self, mock_missing_files):
        identifier = "test.zip"
        missing_files = ["Figure 2"]
        mock_missing_files.return_value = missing_files
        expected = [
            (
                "WARNING elifecleaner:parse:check_missing_files_by_name: %s "
                "has file missing from expected numeric sequence: %s\n"
            )
            % (identifier, missing_files[0])
        ]
        parse.check_missing_files_by_name([], identifier)
        self.assertEqual(read_log_file_lines(self.log_file), expected)


class TestFindMissingFilesByName(unittest.TestCase):
    def setUp(self):
        self.files = [
            OrderedDict(
                [
                    ("file_type", "figure"),
                    ("id", "2063134"),
                    ("upload_file_nm", "eLife64719_figure1_classB.png"),
                    (
                        "custom_meta",
                        [
                            OrderedDict(
                                [
                                    ("meta_name", "Figure number"),
                                    ("meta_value", "Figure 1"),
                                ]
                            )
                        ],
                    ),
                ]
            ),
            OrderedDict(
                [
                    ("file_type", "figure"),
                    ("id", "2063135"),
                    ("upload_file_nm", "eLife64719_figure2_classB.png"),
                    (
                        "custom_meta",
                        [
                            OrderedDict(
                                [
                                    ("meta_name", "Figure number"),
                                    ("meta_value", "Figure 2"),
                                ]
                            )
                        ],
                    ),
                ]
            ),
        ]

    def test_find_missing_files_by_name_empty(self):
        files = []
        expected = []
        self.assertEqual(parse.find_missing_files_by_name(files), expected)

    def test_find_missing_files_by_name_complete(self):
        expected = []
        self.assertEqual(parse.find_missing_files_by_name(self.files), expected)

    def test_find_missing_files_by_name_missing(self):
        self.files[1]["custom_meta"][0]["meta_value"] = "Figure 3"
        expected = ["Figure 2"]
        self.assertEqual(parse.find_missing_files_by_name(self.files), expected)

    def test_find_missing_files_by_name_extra_whitespace(self):
        "test pattern matching if there is whitespace"
        self.files[1]["custom_meta"][0]["meta_value"] = "Figure  \t     3"
        expected = ["Figure 2"]
        self.assertEqual(parse.find_missing_files_by_name(self.files), expected)

    def test_find_file_detail_values_empty(self):
        files = []
        file_types = []
        meta_names = []
        expected = []
        self.assertEqual(
            parse.find_file_detail_values(files, file_types, meta_names), expected
        )

    def test_find_file_detail_values(self):
        files = [
            {
                "file_type": "figure",
                "custom_meta": [
                    {
                        "meta_name": "Title",
                        "meta_value": "Figure 1",
                    }
                ],
            },
            {
                "file_type": "figure",
                "custom_meta": [
                    {
                        "meta_name": "Figure number",
                        "meta_value": "Figure 2",
                    },
                    {
                        "meta_name": "Title",
                        "meta_value": "Second value will be ignored",
                    },
                ],
            },
            {
                "file_type": "additional_figure_data",
                "custom_meta": [
                    {
                        "meta_name": "Figure number",
                        "meta_value": "Figure 2-figure supplement 1",
                    }
                ],
            },
            {
                "file_type": "not_a_figure",
                "custom_meta": [
                    {
                        "meta_name": "Title",
                        "meta_value": "Figure 3",
                    }
                ],
            },
        ]
        file_types = ["figure"]
        meta_names = ["Title", "Figure number"]
        expected = [("figure", "Figure 1"), ("figure", "Figure 2")]
        self.assertEqual(
            parse.find_file_detail_values(files, file_types, meta_names), expected
        )

    def test_find_missing_value_by_sequence(self):
        "test for matching double-digit numbers"
        match_pattern = r"Figure (\d+)"
        values = [
            "Figure 1",
            "Figure 2",
            "Figure 3",
            "Figure 4",
            "Figure 5",
            "Figure 6",
            "Figure 7",
            "Figure 8",
            "Figure 9",
            "Figure 10",
            "Figure 11",
            "Figure 13",
        ]

        expected = ["Figure 12"]
        self.assertEqual(
            parse.find_missing_value_by_sequence(values, match_pattern), expected
        )


class TestCheckArtFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_check_art_file(self):
        "test for an acceptable file type will produce no warning"
        identifier = "test.zip"
        files = [
            OrderedDict(
                [
                    ("file_type", "art_file"),
                    ("upload_file_nm", "test.Docx"),
                ]
            )
        ]
        expected = []
        parse.check_art_file(files, identifier)
        self.assertEqual(read_log_file_lines(self.log_file), expected)

    def test_check_art_file_bad_extension(self):
        "test an unacceptable file type will produce a warning"
        identifier = "test.zip"
        files = [
            OrderedDict(
                [
                    ("file_type", "art_file"),
                    ("upload_file_nm", "test.pdf"),
                ]
            )
        ]
        expected = [
            (
                (
                    "WARNING elifecleaner:parse:check_art_file: %s could not find a "
                    "word or latex article file in the package\n"
                )
            )
            % (identifier)
        ]
        parse.check_art_file(files, identifier)
        self.assertEqual(read_log_file_lines(self.log_file), expected)

    def test_check_art_file_missing(self):
        "test if there is no art_file it will produce a warning"
        identifier = "test.zip"
        files = [OrderedDict()]
        expected = [
            (
                (
                    "WARNING elifecleaner:parse:check_art_file: %s could not find a "
                    "word or latex article file in the package\n"
                )
            )
            % (identifier)
        ]
        parse.check_art_file(files, identifier)
        self.assertEqual(read_log_file_lines(self.log_file), expected)


class TestParsePreprintUrl(unittest.TestCase):
    def test_preprint_url(self):
        xml_string = """<article xmlns:xlink="http://www.w3.org/1999/xlink">
    <front>
        <article-meta>
            <fn-group content-type="article-history">
                <title>Preprint</title>
                <fn fn-type="other"/>
                <ext-link ext-link-type="url" xlink:href="https://doi.org/10.1101/2021.06.02.446694"/>
            </fn-group>
        </article-meta>
    </front>
</article>"""
        expected = "https://doi.org/10.1101/2021.06.02.446694"
        root = ElementTree.fromstring(xml_string)
        result = parse.preprint_url(root)
        self.assertEqual(result, expected)

    def test_preprint_url_no_article_meta(self):
        xml_string = """<article xmlns:xlink="http://www.w3.org/1999/xlink">
    <front></front>
</article>"""
        expected = None
        root = ElementTree.fromstring(xml_string)
        result = parse.preprint_url(root)
        self.assertEqual(result, expected)

    def test_preprint_url_no_ext_link(self):
        xml_string = """<article xmlns:xlink="http://www.w3.org/1999/xlink">
    <front>
        <article-meta>
            <fn-group content-type="article-history"></fn-group>
        </article-meta>
    </front>
</article>"""
        expected = None
        root = ElementTree.fromstring(xml_string)
        result = parse.preprint_url(root)
        self.assertEqual(result, expected)
