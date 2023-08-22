import os
import unittest
from xml.etree import ElementTree
from elifetools import xmlio
from elifecleaner import configure_logging, fig, LOGGER
from tests.helpers import (
    delete_files_in_folder,
    read_log_file_lines,
    sub_article_xml_fixture,
)


class TestInfFileIdentifier(unittest.TestCase):
    "tests for fig.inf_file_identifier()"

    def test_inf_file_identifer(self):
        "identifier portion of an inline-graphic file name"
        inf_file_name = "elife-70493-inf1.png"
        expected = "inf1"
        self.assertEqual(fig.inf_file_identifier(inf_file_name), expected)


class TestFigFileNameIdentifer(unittest.TestCase):
    "tests for fig.fig_file_name_identifier()"

    def test_fig_file_name_identifier(self):
        "generate a fig graphic id value"
        sub_article_id = "sa2"
        fig_index = "1"
        expected = "sa2-fig1"
        self.assertEqual(
            fig.fig_file_name_identifier(sub_article_id, fig_index), expected
        )


class TestFigFileName(unittest.TestCase):
    "tests for fig.fig_file_name()"

    def test_fig_file_name(self):
        "generate a fig graphic file name from an inline-graphic file name"
        inf_file_name = "elife-70493-inf1.png"
        sub_article_id = "sa2"
        fig_index = "1"
        expected = "elife-70493-sa2-fig1.png"
        self.assertEqual(
            fig.fig_file_name(inf_file_name, sub_article_id, fig_index),
            expected,
        )


class TestFigTagIndexGroups(unittest.TestCase):
    "tests for fig.fig_tag_index_groups()"

    def test_fig_tag_index_groups(self):
        "test finding a group of p tags to be converted to a fig"
        xml_string = (
            b'<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<p>First paragraph.</p>"
            b"<p><bold>Review image 1.</bold></p>"
            b"<p>This is the caption for this image that describes what it contains.</p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf1.png" /> </p>'
            b"<p>Another paragraph with an inline graphic "
            b'<inline-graphic xlink:href="elife-70493-inf2.jpg" /></p>'
            b"</body>"
        )
        expected = [{"label_index": 1, "caption_index": 2, "inline_graphic_index": 3}]
        result = fig.fig_tag_index_groups(
            ElementTree.fromstring(xml_string), None, None
        )
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected[0])

    def test_multiple_figs(self):
        "test multiple groups of p tags to be converted to fig tags"
        xml_string = (
            b'<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<p>First paragraph.</p>"
            b"<p><bold>Review image 1.</bold></p>"
            b"<p>This is the caption for this image that describes what it contains.</p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf1.png" /> </p>'
            b"<p><bold>Review image 2</bold></p>"
            b'<p><inline-graphic xlink:href="elife-70493-inf2.jpg" /></p>'
            b"</body>"
        )
        expected = [
            {"label_index": 1, "caption_index": 2, "inline_graphic_index": 3},
            {"label_index": 4, "caption_index": False, "inline_graphic_index": 5},
        ]
        result = fig.fig_tag_index_groups(
            ElementTree.fromstring(xml_string), None, None
        )
        self.assertEqual(len(result), 2)
        # first fig
        self.assertDictEqual(result[0], expected[0])
        # second fig
        self.assertDictEqual(result[1], expected[1])

    def test_empty(self):
        "test if no p tag groups are found"
        xml_string = (
            b'<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<p>First paragraph.</p>"
            b"</body>"
        )
        result = fig.fig_tag_index_groups(
            ElementTree.fromstring(xml_string), None, None
        )
        self.assertEqual(len(result), 0)

    def test_none(self):
        "test None as input to finding p tag groups"
        result = fig.fig_tag_index_groups(None, None, None)
        self.assertEqual(result, [])


class TestTransformFigGroups(unittest.TestCase):
    "tests for fig.transform_fig_groups()"

    def test_transform_fig_groups(self):
        "give body tag and indexes of p tags to transform to a fig tag"
        # register XML namespaces
        xmlio.register_xmlns()
        xml_string = (
            b'<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<p>First paragraph.</p>"
            b"<p><bold>Review image 1.</bold></p>"
            b"<p>This is the caption for this image that describes what it contains.</p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf1.png" /> </p>'
            b"<p><bold>Review image 2</bold></p>"
            b'<p><inline-graphic xlink:href="elife-70493-inf2.jpg" /></p>'
            b"</body>"
        )
        body_tag = ElementTree.fromstring(xml_string)
        fig_index_groups = [
            {"label_index": 1, "caption_index": 2, "inline_graphic_index": 3},
            {"label_index": 4, "caption_index": False, "inline_graphic_index": 5},
        ]
        sub_article_id = "sa1"
        expected = (
            b'<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<p>First paragraph.</p>"
            b'<fig id="sa1fig1">'
            b"<label>Review image 1.</label>"
            b"<caption>"
            b"<title>"
            b"This is the caption for this image that describes what it contains."
            b"</title>"
            b"</caption>"
            b'<graphic mimetype="image" mime-subtype="png" xlink:href="elife-70493-sa1-fig1.png" />'
            b"</fig>"
            b'<fig id="sa1fig2">'
            b"<label>Review image 2</label>"
            b'<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-70493-sa1-fig2.jpg" />'
            b"</fig>"
            b"</body>"
        )
        fig.transform_fig_groups(body_tag, fig_index_groups, sub_article_id)
        self.assertEqual(ElementTree.tostring(body_tag), expected)


class TestRemoveTagAttributes(unittest.TestCase):
    "tests for fig.remove_tag_attributes()"

    def test_remove_tag_attributes(self):
        "test cleaning attributes from a p tag"
        # register XML namespaces
        xmlio.register_xmlns()
        xml_string = (
            b'<p xmlns:xlink="http://www.w3.org/1999/xlink" id="p" xlink:href="foo" />'
        )
        tag = ElementTree.fromstring(xml_string)
        expected = b"<p />"
        fig.remove_tag_attributes(tag)
        self.assertEqual(ElementTree.tostring(tag), expected)

    def test_non_element(self):
        "test if the input is not a tag"
        tag = "foo"
        self.assertEqual(fig.remove_tag_attributes(tag), None)


class TestInlineGraphicHrefs(unittest.TestCase):
    "tests for fig.inline_graphic_hrefs()"

    def test_inline_graphic_hrefs(self):
        "get a list of xlink:href values from inline-graphic tags to be converted to fig"
        xml_string = (
            b'<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<body>"
            b"<p><bold>Review image 1.</bold></p>"
            b'<p><inline-graphic xlink:href="elife-70493-inf1.png"/></p>'
            b"<p>Next paragraph is not an inline-graphic href.</p>"
            b'<p><inline-graphic xlink:href="elife-70493-inf2.png"/></p>'
            b"</body>"
            b"</sub-article>"
        )
        identifier = "test.zip"
        tag = ElementTree.fromstring(xml_string)
        expected = ["elife-70493-inf1.png"]
        result = fig.inline_graphic_hrefs(tag, identifier)
        self.assertEqual(result, expected)


class TestGraphicHrefs(unittest.TestCase):
    "tests for fig.graphic_hrefs()"

    def test_graphic_hrefs(self):
        "get a list of xlink:href values from graphic tags"
        xml_string = (
            b'<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink"><body>'
            b"<p>"
            b'<fig id="sa1fig1">'
            b"<label>Review image 1.</label>"
            b"<caption>"
            b"<title>A title.</title>"
            b"<p>A caption.</p>"
            b"</caption>"
            b'<graphic mimetype="image" mime-subtype="png" xlink:href="elife-70493-sa1-fig1.png" />'
            b"</fig>"
            b"</p>"
            b"</body></sub-article>"
        )
        identifier = "test.zip"
        tag = ElementTree.fromstring(xml_string)
        expected = ["elife-70493-sa1-fig1.png"]
        result = fig.graphic_hrefs(tag, identifier)
        self.assertEqual(result, expected)

    def test_graphic_hrefs_no_match(self):
        "empty list of xlink:href values when there is no graphic tag"
        xml_string = (
            b'<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<body><p/></body>"
            b"</sub-article>"
        )
        identifier = "test.zip"
        tag = ElementTree.fromstring(xml_string)
        expected = []
        result = fig.graphic_hrefs(tag, identifier)
        self.assertEqual(result, expected)


class TestTransformFigGroup(unittest.TestCase):
    "tests for fig.transform_fig_group()"

    def test_transform_fig_group(self):
        "give body tag and indexes of p tags to transform to a fig tag"
        # register XML namespaces
        xmlio.register_xmlns()
        xml_string = (
            b'<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<p>First paragraph.</p>"
            b"<p><bold>Review image 1.</bold></p>"
            b"<p>This is the caption for this image that describes what it contains.</p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf1.png" /> </p>'
            b"</body>"
        )
        body_tag = ElementTree.fromstring(xml_string)
        fig_index = 1
        fig_group = {"label_index": 1, "caption_index": 2, "inline_graphic_index": 3}
        sub_article_id = "sa1"
        expected = (
            b'<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<p>First paragraph.</p>"
            b'<fig id="sa1fig1">'
            b"<label>Review image 1.</label>"
            b"<caption>"
            b"<title>"
            b"This is the caption for this image that describes what it contains."
            b"</title>"
            b"</caption>"
            b'<graphic mimetype="image" mime-subtype="png" xlink:href="elife-70493-sa1-fig1.png" />'
            b"</fig>"
            b"</body>"
        )

        fig.transform_fig_group(body_tag, fig_index, fig_group, sub_article_id)
        self.assertEqual(ElementTree.tostring(body_tag), expected)


def sa1_sub_article_xml_fixture():
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
        b"<p><bold>Review image 1.</bold></p>"
        b"<p>This is the caption for this image that describes what it contains.</p>"
        b'<p> <inline-graphic xlink:href="elife-70493-inf1.png" /> </p>'
        b"<p>Another paragraph with an inline graphic "
        b'<inline-graphic xlink:href="elife-70493-inf2.jpg" /></p>'
        b"</body>"
    )
    return sub_article_xml_fixture(
        article_type, sub_article_id, front_stub_xml_string, body_xml_string
    )


def sa4_sub_article_xml_fixture(body_xml_string):
    "generate XML test fixture for an author-comment"
    article_type = b"author-comment"
    sub_article_id = b"sa4"
    front_stub_xml_string = (
        b"<front-stub>"
        b'<article-id pub-id-type="doi">10.7554/eLife.79713.1.sa4</article-id>'
        b"<title-group><article-title>Author response</article-title></title-group>"
        b"</front-stub>"
    )
    return sub_article_xml_fixture(
        article_type, sub_article_id, front_stub_xml_string, body_xml_string
    )


class TestTransformFig(unittest.TestCase):
    "tests for fig.transform_fig()"

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
        xml_string = sa1_sub_article_xml_fixture()
        sub_article_root = ElementTree.fromstring(xml_string)
        root = fig.transform_fig(sub_article_root, self.identifier)

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertTrue("<p>First paragraph.</p>" in rough_xml_string.decode("utf8"))
        self.assertTrue(
            '<inline-graphic xlink:href="elife-70493-inf2.jpg" />'
            in rough_xml_string.decode("utf8")
        )
        print(rough_xml_string.decode("utf8"))
        self.assertTrue(
            (
                "<body>"
                "<p>First paragraph.</p>"
                '<fig id="sa1fig1">'
                "<label>Review image 1.</label>"
                "<caption>"
                "<title>"
                "This is the caption for this image that describes what it contains."
                "</title>"
                "</caption>"
                '<graphic mimetype="image" mime-subtype="png" '
                'xlink:href="elife-70493-sa1-fig1.png" />'
                "</fig>"
                "<p>Another paragraph with an inline graphic "
                '<inline-graphic xlink:href="elife-70493-inf2.jpg" />'
                "</p>"
                "</body>"
            )
            in rough_xml_string.decode("utf8")
        )
        info_prefix = "INFO elifecleaner:block"
        expected = [
            '%s:%s: %s potential label "Review image 1." in p tag 1 of id sa1\n'
            % (info_prefix, "is_p_label", self.identifier),
            "%s:%s: %s label p tag index 1 of id sa1\n"
            % (info_prefix, "tag_index_groups", self.identifier),
            "%s:%s: %s no inline-graphic tag found in p tag 2 of id sa1\n"
            % (info_prefix, "is_p_inline_graphic", self.identifier),
            "%s:%s: %s only inline-graphic tag found in p tag 3 of id sa1\n"
            % (info_prefix, "is_p_inline_graphic", self.identifier),
        ]
        self.assertEqual(read_log_file_lines(self.log_file), expected)

    def test_author_response(self):
        "convert tags to a fig in an author-comment fixture"
        # register XML namespaces
        xmlio.register_xmlns()
        body_xml_string = (
            b"<body>"
            b"<p>First paragraph.</p>"
            b"<p><bold>Author response image 1.</bold></p>"
            b"<p>This is the caption for this image that describes what it contains.</p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf3.png" /> </p>'
            b"<p>Another paragraph with an inline graphic "
            b'<inline-graphic xlink:href="elife-70493-inf4.jpg" /></p>'
            b"</body>"
        )
        xml_string = sa4_sub_article_xml_fixture(body_xml_string)

        sub_article_root = ElementTree.fromstring(xml_string)
        root = fig.transform_fig(sub_article_root, self.identifier)

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertTrue("<p>First paragraph.</p>" in rough_xml_string.decode("utf8"))
        self.assertTrue(
            '<inline-graphic xlink:href="elife-70493-inf4.jpg" />'
            in rough_xml_string.decode("utf8")
        )
        self.assertTrue(
            (
                "<body>"
                "<p>First paragraph.</p>"
                '<fig id="sa4fig1">'
                "<label>Author response image 1.</label>"
                "<caption>"
                "<title>"
                "This is the caption for this image that describes what it contains."
                "</title>"
                "</caption>"
                '<graphic mimetype="image" mime-subtype="png" '
                'xlink:href="elife-70493-sa4-fig1.png" />'
                "</fig>"
                "<p>Another paragraph with an inline graphic "
                '<inline-graphic xlink:href="elife-70493-inf4.jpg" />'
                "</p>"
                "</body>"
            )
            in rough_xml_string.decode("utf8")
        )
        info_prefix = "INFO elifecleaner:block"
        expected = [
            '%s:%s: %s potential label "Author response image 1." in p tag 1 of id sa4\n'
            % (info_prefix, "is_p_label", self.identifier),
            "%s:%s: %s label p tag index 1 of id sa4\n"
            % (info_prefix, "tag_index_groups", self.identifier),
            "%s:%s: %s no inline-graphic tag found in p tag 2 of id sa4\n"
            % (info_prefix, "is_p_inline_graphic", self.identifier),
            "%s:%s: %s only inline-graphic tag found in p tag 3 of id sa4\n"
            % (info_prefix, "is_p_inline_graphic", self.identifier),
        ]
        self.assertEqual(read_log_file_lines(self.log_file), expected)

    def test_caption_italic(self):
        "convert tags to a fig where the caption has an inline intalic tag"
        # register XML namespaces
        xmlio.register_xmlns()

        body_xml_string = (
            b"<body>"
            b"<p>First paragraph.</p>"
            b"<p><bold>Author response image 1.</bold></p>"
            b'<p>Caption with an <italic id="foo">italic</italic> tag or '
            b"<bold>bold</bold> too.</p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf3.png" /> </p>'
            b"<p>Another paragraph with an inline graphic "
            b'<inline-graphic xlink:href="elife-70493-inf4.jpg" /></p>'
            b"</body>"
        )

        xml_string = sa4_sub_article_xml_fixture(body_xml_string)
        sub_article_root = ElementTree.fromstring(xml_string)
        root = fig.transform_fig(sub_article_root, self.identifier)

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertTrue(
            (
                "<body>"
                "<p>First paragraph.</p>"
                '<fig id="sa4fig1">'
                "<label>Author response image 1.</label>"
                "<caption>"
                "<title>"
                'Caption with an <italic id="foo">italic</italic> tag or <bold>bold</bold> too.'
                "</title>"
                "</caption>"
                '<graphic mimetype="image" mime-subtype="png" '
                'xlink:href="elife-70493-sa4-fig1.png" />'
                "</fig>"
                "<p>Another paragraph with an inline graphic "
                '<inline-graphic xlink:href="elife-70493-inf4.jpg" />'
                "</p>"
                "</body>"
            )
            in rough_xml_string.decode("utf8")
        )

    def test_no_caption(self):
        "convert tags to a fig where there is no p tag for the caption content"
        # register XML namespaces
        xmlio.register_xmlns()
        body_xml_string = (
            b"<body>"
            b"<p>First paragraph.</p>"
            b"<p><bold>Author response image 1.</bold></p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf3.png" /> </p>'
            b"<p>Another paragraph with an inline graphic "
            b'<inline-graphic xlink:href="elife-70493-inf4.jpg" /></p>'
            b"</body>"
        )
        xml_string = sa4_sub_article_xml_fixture(body_xml_string)

        sub_article_root = ElementTree.fromstring(xml_string)
        root = fig.transform_fig(sub_article_root, self.identifier)

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertTrue(
            (
                "<body>"
                "<p>First paragraph.</p>"
                '<fig id="sa4fig1">'
                "<label>Author response image 1.</label>"
                '<graphic mimetype="image" mime-subtype="png" '
                'xlink:href="elife-70493-sa4-fig1.png" />'
                "</fig>"
                "<p>Another paragraph with an inline graphic "
                '<inline-graphic xlink:href="elife-70493-inf4.jpg" />'
                "</p>"
                "</body>"
            )
            in rough_xml_string.decode("utf8")
        )

    def test_multiple_caption(self):
        "test if there are multiple caption p tags before the inline-graphic tag"
        # register XML namespaces
        xmlio.register_xmlns()
        body_xml_string = (
            b"<body>"
            b"<p>First paragraph.</p>"
            b"<p><bold>Author response image 1.</bold></p>"
            b"<p>Caption paragraph one.</p>"
            b"<p>Caption paragraph two.</p>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf3.png" /> </p>'
            b"<p>Another paragraph with an inline graphic "
            b'<inline-graphic xlink:href="elife-70493-inf4.jpg" /></p>'
            b"</body>"
        )
        xml_string = sa4_sub_article_xml_fixture(body_xml_string)

        sub_article_root = ElementTree.fromstring(xml_string)
        root = fig.transform_fig(sub_article_root, self.identifier)

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertEqual(xml_string, rough_xml_string)

    def test_non_p_tag(self):
        "test if the p tag order is disrupted with a sec tag"
        # register XML namespaces
        xmlio.register_xmlns()

        body_xml_string = (
            b"<body>"
            b"<p>First paragraph.</p>"
            b"<p><bold>Author response image 1.</bold></p>"
            b"<sec>Non-p tag</sec>"
            b'<p> <inline-graphic xlink:href="elife-70493-inf3.png" /> </p>'
            b"<p>Another paragraph with an inline graphic "
            b'<inline-graphic xlink:href="elife-70493-inf4.jpg" /></p>'
            b"</body>"
        )
        xml_string = sa4_sub_article_xml_fixture(body_xml_string)

        sub_article_root = ElementTree.fromstring(xml_string)
        root = fig.transform_fig(sub_article_root, self.identifier)

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertEqual(xml_string, rough_xml_string)
