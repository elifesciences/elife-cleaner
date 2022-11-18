import os
import unittest
from xml.etree import ElementTree
from elifecleaner import LOGGER, configure_logging, prc
from tests.helpers import delete_files_in_folder

# elife ISSN example of non-PRC journal-id tag values
NON_PRC_XML = (
    "<article><front><journal-meta>"
    '<journal-id journal-id-type="nlm-ta">elife</journal-id>'
    '<journal-id journal-id-type="hwp">eLife</journal-id>'
    '<journal-id journal-id-type="publisher-id">eLife</journal-id>'
    "<journal-title-group>"
    "<journal-title>eLife</journal-title>"
    "</journal-title-group>"
    '<issn pub-type="epub">2050-084X</issn>'
    "<publisher>"
    "<publisher-name>eLife Sciences Publications, Ltd</publisher-name>"
    "</publisher>"
    "</journal-meta></front></article>"
)

# PRC xml will have non-eLife journal-id tag text values
PRC_XML = (
    "<article><front><journal-meta>"
    '<journal-id journal-id-type="nlm-ta">foo</journal-id>'
    '<journal-id journal-id-type="hwp">foo</journal-id>'
    '<journal-id journal-id-type="publisher-id">foo</journal-id>'
    "<journal-title-group>"
    "<journal-title>eLife</journal-title>"
    "</journal-title-group>"
    '<issn pub-type="epub">2050-084X</issn>'
    "<publisher>"
    "<publisher-name>eLife Sciences Publications, Ltd</publisher-name>"
    "</publisher>"
    "</journal-meta></front></article>"
)


class TestIsXmlPrc(unittest.TestCase):
    def test_is_xml_prc(self):
        "PRC XML will return true"
        root = ElementTree.fromstring(PRC_XML)
        self.assertTrue(prc.is_xml_prc(root))

    def test_is_xml_prc_false(self):
        "test non-PRC XML will return false"
        root = ElementTree.fromstring(NON_PRC_XML)
        self.assertEqual(prc.is_xml_prc(root), False)

    def test_is_xml_prc_incomplete(self):
        "incomplete XML will return false"
        root = ElementTree.fromstring("<root/>")
        self.assertEqual(prc.is_xml_prc(root), False)


class TestTransformJournalIdTags(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_transform_journal_id_tags(self):
        # populate an ElementTree
        identifier = "test.zip"
        xml_string = PRC_XML
        expected = bytes(NON_PRC_XML, encoding="utf-8")
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.transform_journal_id_tags(root, identifier)
        # assertions
        self.assertEqual(ElementTree.tostring(root_output), expected)
        log_file_lines = []
        with open(self.log_file, "r") as open_file:
            for line in open_file:
                log_file_lines.append(line)
        for index, (journal_id_type, tag_text) in enumerate(
            [("nlm-ta", "elife"), ("hwp", "eLife"), ("publisher-id", "eLife")]
        ):
            self.assertEqual(
                log_file_lines[index],
                (
                    (
                        "INFO elifecleaner:prc:transform_journal_id_tags: "
                        "%s replacing journal-id tag text of type %s to %s\n"
                    )
                )
                % (identifier, journal_id_type, tag_text),
            )


class TestAddPrcCustomMetaTags(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.expected_xml = bytes(
            "<article>"
            "<front>"
            "<article-meta>"
            "<custom-meta-group>"
            '<custom-meta specific-use="meta-only">'
            "<meta-name>publishing-route</meta-name>"
            "<meta-value>prc</meta-value>"
            "</custom-meta>"
            "</custom-meta-group>"
            "</article-meta>"
            "</front>"
            "</article>",
            encoding="utf-8",
        )

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_add_custom_meta_tags(self):
        "test when custom-meta-group tag does not yet exist"
        # populate an ElementTree
        xml_string = "<article><front><article-meta/></front></article>"
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.add_prc_custom_meta_tags(root)
        # assertions
        self.assertEqual(ElementTree.tostring(root_output), self.expected_xml)

    def test_group_tag_exists(self):
        "test if custom-meta-group tag already exists"
        # populate an ElementTree
        xml_string = (
            "<article><front><article-meta>"
            "<custom-meta-group />"
            "</article-meta></front></article>"
        )
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.add_prc_custom_meta_tags(root)
        # assertions
        self.assertEqual(ElementTree.tostring(root_output), self.expected_xml)

    def test_no_article_meta_tag(self):
        # populate an ElementTree
        identifier = "test.zip"
        xml_string = "<root/>"
        expected = b"<root />"
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.add_prc_custom_meta_tags(root, identifier)
        # assertions
        self.assertEqual(ElementTree.tostring(root_output), expected)
        with open(self.log_file, "r") as open_file:
            self.assertEqual(
                open_file.read(),
                (
                    "WARNING elifecleaner:prc:add_prc_custom_meta_tags: "
                    "%s article-meta tag not found\n"
                )
                % identifier,
            )


class TestTransformElocationId(unittest.TestCase):
    def setUp(self):
        self.xml_string_pattern = (
            "<article><front><article-meta>%s</article-meta></front></article>"
        )

    def test_transform_elocation_id(self):
        xml_string = (
            self.xml_string_pattern % "<elocation-id>e1234567890</elocation-id>"
        )
        expected = bytes(
            self.xml_string_pattern % "<elocation-id>RP1234567890</elocation-id>",
            encoding="utf-8",
        )
        identifier = "test.zip"
        root = ElementTree.fromstring(xml_string)
        root_output = prc.transform_elocation_id(root, identifier=identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_no_change(self):
        xml_string = self.xml_string_pattern % "<elocation-id>foo</elocation-id>"
        expected = bytes(xml_string, encoding="utf-8")
        root = ElementTree.fromstring(xml_string)
        root_output = prc.transform_elocation_id(root)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_tag_missing(self):
        xml_string = "<article />"
        expected = bytes(xml_string, encoding="utf-8")
        root = ElementTree.fromstring(xml_string)
        root_output = prc.transform_elocation_id(root)
        self.assertEqual(ElementTree.tostring(root_output), expected)
