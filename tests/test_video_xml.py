import unittest
import os
import sys
import time
import zipfile
from collections import OrderedDict
from xml.etree import ElementTree
from mock import patch
from elifearticle.article import Article, ArticleDate
from elifecleaner import video_xml
from tests.helpers import delete_files_in_folder, read_fixture

JOURNAL_DATA = {
    "journal_ids": {"nlm-ta": "elife", "publisher-id": "eLife"},
    "journal_title": "eLife",
    "publisher_name": "eLife Sciences Publications, Ltd",
}

VIDEO_DATA = [
    OrderedDict(
        [
            ("upload_file_nm", "Video 1 AVI.avi"),
            ("video_id", "video1"),
            ("video_filename", "elife-64719-video1.avi"),
        ]
    )
]


def build_article(doi=None, manuscript=None):
    article = Article(doi=doi)
    article.manuscript = manuscript
    return article


class TestSetPubDate(unittest.TestCase):
    def test_set_pub_date(self):
        root = ElementTree.fromstring("<article/>")
        article = build_article()
        pub_type = "electronic"
        date_time = time.strptime("2022-04-19", "%Y-%m-%d")
        article.add_date(ArticleDate(pub_type, date_time))
        expected = (
            b"<article>"
            b'<pub-date date-type="%s">'
            b"<day>19</day>"
            b"<month>04</month>"
            b"<year>2022</year>"
            b"</pub-date>"
            b"</article>" % bytes(pub_type, "utf-8")
        )
        video_xml.set_pub_date(root, article, pub_type)
        xml_string = ElementTree.tostring(root, "utf-8")
        self.assertEqual(xml_string, expected)


class TestSetArticleMeta(unittest.TestCase):
    def test_set_article_meta(self):
        root = ElementTree.fromstring("<article/>")
        article = build_article("10.7554/eLife.64719", 64719)
        expected = (
            b"<article>"
            b"<article-meta>"
            b'<article-id pub-id-type="publisher-id">64719</article-id>'
            b'<article-id pub-id-type="doi">10.7554/eLife.64719</article-id>'
            b"</article-meta>"
            b"</article>"
        )
        video_xml.set_article_meta(root, article)
        xml_string = ElementTree.tostring(root, "utf-8")
        self.assertEqual(xml_string, expected)


class TestSetFront(unittest.TestCase):
    def test_set_front(self):
        root = ElementTree.fromstring("<article/>")
        article = build_article("10.7554/eLife.64719", 64719)
        expected = (
            b"<article>"
            b"<front>"
            b"<journal-meta>"
            b'<journal-id journal-id-type="nlm-ta">elife</journal-id>'
            b'<journal-id journal-id-type="publisher-id">eLife</journal-id>'
            b"<journal-title-group>"
            b"<journal-title>eLife</journal-title>"
            b"</journal-title-group>"
            b"<publisher>"
            b"<publisher-name>eLife Sciences Publications, Ltd</publisher-name>"
            b"</publisher>"
            b"</journal-meta>"
            b"<article-meta>"
            b'<article-id pub-id-type="publisher-id">64719</article-id>'
            b'<article-id pub-id-type="doi">10.7554/eLife.64719</article-id>'
            b"</article-meta>"
            b"</front>"
            b"</article>"
        )
        video_xml.set_front(root, JOURNAL_DATA, article)
        xml_string = ElementTree.tostring(root, "utf-8")
        self.assertEqual(xml_string, expected)


class TestBody(unittest.TestCase):
    def test_set_body(self):
        root = ElementTree.fromstring("<article/>")
        media_tag_xml_string = (
            b'<media xlink:href="elife-64719-video1.avi" id="video1" '
            b'content-type="glencoe play-in-place height-250 width-310" mimetype="video" />'
        )
        if sys.version_info < (3, 8):
            # pre Python 3.8 tag attributes are automatically alphabetised
            media_tag_xml_string = (
                b'<media content-type="glencoe play-in-place height-250 width-310" '
                b'id="video1" mimetype="video" xlink:href="elife-64719-video1.avi" />'
            )
        expected = (
            b"<article>" b"<body>" + media_tag_xml_string + b"</body>" b"</article>"
        )
        video_xml.set_body(root, VIDEO_DATA)
        xml_string = ElementTree.tostring(root, "utf-8")
        self.assertEqual(xml_string, expected)


class TestOutputXml(unittest.TestCase):
    def test_output_xml(self):
        xml_string = "<article/>"
        root = ElementTree.fromstring(xml_string)
        expected = b'<?xml version="1.0" encoding="utf-8"?>' + bytes(
            xml_string, "utf-8"
        )
        output = video_xml.output_xml(root)
        self.assertEqual(output, expected)

    def test_output_xml_pretty(self):
        xml_string = "<article/>"
        root = ElementTree.fromstring(xml_string)
        expected = (
            b'<?xml version="1.0" encoding="utf-8"?>'
            + b"\n"
            + bytes(xml_string, "utf-8")
            + b"\n"
        )
        output = video_xml.output_xml(root, pretty=True)
        self.assertEqual(output, expected)


class TestGenerateXml(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.video_xml_64719 = read_fixture("video_xml_64719.xml", "rb")
        if sys.version_info < (3, 8):
            # pre Python 3.8 tag attributes are automatically alphabetised
            self.video_xml_64719 = self.video_xml_64719.replace(
                b'<article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" dtd-version="1.1d1" article-type="research-article">',
                b'<article article-type="research-article" dtd-version="1.1d1" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink">',
            )
            self.video_xml_64719 = self.video_xml_64719.replace(
                b'<media xlink:href="elife-64719-video1.avi" id="video1" content-type="glencoe play-in-place height-250 width-310" mimetype="video"/>',
                b'<media content-type="glencoe play-in-place height-250 width-310" id="video1" mimetype="video" xlink:href="elife-64719-video1.avi"/>',
            )

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    @patch.object(time, "gmtime")
    def test_glencoe_xml(self, fake_gmtime):
        fake_gmtime.return_value = time.strptime("2022-04-19", "%Y-%m-%d")
        zip_file = "tests/test_data/08-11-2020-FA-eLife-64719.zip"
        xml_file_name = "08-11-2020-FA-eLife-64719/08-11-2020-FA-eLife-64719.xml"
        xml_file_path = os.path.join(self.temp_dir, xml_file_name)
        with zipfile.ZipFile(zip_file, "r") as input_zipfile:
            input_zipfile.extract(xml_file_name, self.temp_dir)
        xml_string = video_xml.glencoe_xml(xml_file_path, VIDEO_DATA)
        self.assertEqual(xml_string, self.video_xml_64719)

    @patch.object(time, "gmtime")
    def test_generate_xml(self, fake_gmtime):
        fake_gmtime.return_value = time.strptime("2022-04-19", "%Y-%m-%d")
        article = build_article("10.7554/eLife.64719", 64719)
        xml_string = video_xml.generate_xml(article, JOURNAL_DATA, VIDEO_DATA)
        self.assertEqual(xml_string, self.video_xml_64719)
