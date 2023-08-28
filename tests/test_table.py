import os
import unittest
from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from elifetools import xmlio
from elifecleaner import configure_logging, table, LOGGER
from tests.helpers import (
    delete_files_in_folder,
    read_fixture,
    read_log_file_lines,
    sub_article_xml_fixture,
)


def table_sub_article_xml_fixture():
    "generate XML test fixture for a referee-report"
    article_type = b"referee-report"
    sub_article_id = b"sa1"
    front_stub_xml_string = (
        b"<front-stub>"
        b'<article-id pub-id-type="doi">10.7554/eLife.79713.1.sa1</article-id>'
        b"<title-group>"
        b"<article-title>Reviewer #1 (Public Review):</article-title>"
        b"</title-group>"
        b"</front-stub>"
    )
    body_xml_string = (
        b"<body>"
        b"<p>First paragraph.</p>"
        b"<p><bold>Review table 1.</bold></p>"
        b"<p>Table title. This is the caption for this table that describes what it contains.</p>"
        b'<p> <inline-graphic xlink:href="elife-70493-inf1.png" /> </p>'
        b"<p>Another paragraph with an inline graphic "
        b'<inline-graphic xlink:href="elife-70493-inf2.jpg" /></p>'
        b"</body>"
    )
    return sub_article_xml_fixture(
        article_type, sub_article_id, front_stub_xml_string, body_xml_string
    )


class TestTransformTable(unittest.TestCase):
    "tests for table.transform_table()"

    def setUp(self):
        self.identifier = "test.zip"
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_referee_report(self):
        "convert tags to a fig in a referee-report fixture"
        # register XML namespaces
        xmlio.register_xmlns()
        xml_string = table_sub_article_xml_fixture()
        sub_article_root = ElementTree.fromstring(xml_string)
        root = table.transform_table(sub_article_root, self.identifier)

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertTrue("<p>First paragraph.</p>" in rough_xml_string.decode("utf8"))
        self.assertTrue(
            '<inline-graphic xlink:href="elife-70493-inf2.jpg" />'
            in rough_xml_string.decode("utf8")
        )
        self.assertTrue(
            (
                "<body>"
                "<p>First paragraph.</p>"
                '<table-wrap id="sa1table1">'
                "<label>Review table 1.</label>"
                "<caption>"
                "<title>Table title.</title>"
                "<p>This is the caption for this table that describes what it contains.</p>"
                "</caption>"
                '<graphic mimetype="image" mime-subtype="png" xlink:href="elife-70493-inf1.png" />'
                "</table-wrap>"
                "<p>Another paragraph with an inline graphic "
                '<inline-graphic xlink:href="elife-70493-inf2.jpg" />'
                "</p>"
                "</body>"
            )
            in rough_xml_string.decode("utf8")
        )
        block_info_prefix = "INFO elifecleaner:block"
        expected = [
            '%s:%s: %s potential label "Review table 1." in p tag 1 of id sa1\n'
            % (block_info_prefix, "is_p_label", self.identifier),
            "%s:%s: %s label p tag index 1 of id sa1\n"
            % (block_info_prefix, "tag_index_groups", self.identifier),
            "%s:%s: %s no inline-graphic tag found in p tag 2 of id sa1\n"
            % (block_info_prefix, "is_p_inline_graphic", self.identifier),
            "%s:%s: %s only inline-graphic tag found in p tag 3 of id sa1\n"
            % (block_info_prefix, "is_p_inline_graphic", self.identifier),
        ]
        self.assertEqual(read_log_file_lines(self.log_file), expected)


class TestTsvToList(unittest.TestCase):
    "tests for table.tsv_to_list()"

    def test_tsv_to_list(self):
        "test converting tab separated value string to a list"
        tsv_string = read_fixture("85111_table.tsv")
        expected = read_fixture("85111_table.py")
        result = table.tsv_to_list(tsv_string)
        self.assertEqual(result, expected)

    def test_none(self):
        "test None"
        tsv_string = None
        expected = []
        result = table.tsv_to_list(tsv_string)
        self.assertEqual(result, expected)


class TestListToTableXml(unittest.TestCase):
    "tests for table.list_to_table_xml()"

    def setUp(self):
        self.maxDiff = None

    def test_list_to_table_xml(self):
        "test converting a list of rows into an XML table"
        encoding = "utf-8"
        indent = "    "
        table_rows = read_fixture("85111_table.py")
        expected = read_fixture("85111_table.xml")
        result = table.list_to_table_xml(table_rows)
        self.assertTrue(isinstance(result, Element))
        # convert result to a pretty string
        rough_string = ElementTree.tostring(result)
        reparsed = minidom.parseString(rough_string)
        pretty_result = reparsed.toprettyxml(indent, encoding=encoding).decode("utf-8")
        self.assertEqual(pretty_result, expected)

    def test_inline_tag(self):
        "test for inline tags in the table rows"
        table_rows = [["<italic>Italic\n</italic>>"], ["<<bold>&</bold><foo>"]]
        expected = (
            "<table>"
            "<thead>"
            "<tr>"
            "<th><italic>Italic<break /></italic>&gt;</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
            "<tr>"
            "<td>&lt;<bold>&amp;</bold>&lt;foo&gt;</td>"
            "</tr>"
            "</tbody>"
            "</table>"
        )
        result = table.list_to_table_xml(table_rows)
        self.assertTrue(isinstance(result, Element))
        self.assertEqual(ElementTree.tostring(result).decode("utf-8"), expected)
