import unittest
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from elifetools import xmlio
from elifecleaner import block


class TestMatchFigLabelContent(unittest.TestCase):
    "tests for block.match_fig_label_content()"

    def test_match_fig_label_content(self):
        "test matching paragraph content as a fig label"
        cases = [
            (None, False),
            ("", False),
            ("Test", False),
            ("Review image 1.", True),
            ("Review image 1", True),
            ("Review table 1.", False),
            ("Author response image 1.", True),
        ]
        for content, expected in cases:
            self.assertEqual(block.match_fig_label_content(content), expected)


class TestMatchTableLabelContent(unittest.TestCase):
    "tests for block.match_table_label_content()"

    def test_match_table_label_content(self):
        "test matching paragraph content as a table label"
        cases = [
            (None, False),
            ("", False),
            ("Test", False),
            ("Review table 1.", True),
            ("Review table 1", True),
            ("Review image 1.", False),
            ("Author response table 1.", True),
        ]
        for content, expected in cases:
            self.assertEqual(
                block.match_table_label_content(content), expected, 'on "%s"' % content
            )


class TestIsPLabel(unittest.TestCase):
    "tests for block.is_p_label()"

    def test_is_p_label(self):
        "example of a matched label in a p tag"
        xml_string = "<p><bold>Review image 1.</bold></p>"
        block_type = "fig"
        expected = True
        self.assertEqual(
            block.is_p_label(
                ElementTree.fromstring(xml_string), None, None, block_type, None
            ),
            expected,
        )

    def test_table_is_p_label(self):
        "example of a matched table label in a p tag"
        xml_string = "<p><bold>Review table 1.</bold></p>"
        block_type = "table"
        expected = True
        self.assertEqual(
            block.is_p_label(
                ElementTree.fromstring(xml_string), None, None, block_type, None
            ),
            expected,
        )

    def test_no_block_type(self):
        "test if block_type is None"
        xml_string = "<p><bold>Review table 1.</bold></p>"
        block_type = None
        expected = None
        self.assertEqual(
            block.is_p_label(
                ElementTree.fromstring(xml_string), None, None, block_type, None
            ),
            expected,
        )

    def test_false(self):
        "not a label in a p tag"
        xml_string = "<p>Foo.</p>"
        block_type = "fig"
        expected = False
        self.assertEqual(
            block.is_p_label(
                ElementTree.fromstring(xml_string), None, None, block_type, None
            ),
            expected,
        )


class TestIsPInlineGraphic(unittest.TestCase):
    "tests for block.is_p_inline_graphic()"

    def test_is_p_inline_graphic(self):
        "simple example of an inline-graphic p tag"
        xml_string = "<p><inline-graphic /></p>"
        expected = True
        self.assertEqual(
            block.is_p_inline_graphic(
                ElementTree.fromstring(xml_string), None, None, None
            ),
            expected,
        )

    def test_whitespace(self):
        "test if when whitespace surrounds the inline-graphic tag"
        xml_string = "<p>   <inline-graphic />      </p>"
        expected = True
        self.assertEqual(
            block.is_p_inline_graphic(
                ElementTree.fromstring(xml_string), None, None, None
            ),
            expected,
        )

    def test_false(self):
        "not an inline-graphic p tag"
        xml_string = "<p>Foo.</p>"
        expected = False
        self.assertEqual(
            block.is_p_inline_graphic(
                ElementTree.fromstring(xml_string), None, None, None
            ),
            expected,
        )

    def test_none(self):
        "an inline-graphic tag and other content returns None"
        xml_string = "<p>An <inline-graphic/></p>"
        expected = None
        self.assertEqual(
            block.is_p_inline_graphic(
                ElementTree.fromstring(xml_string), None, None, None
            ),
            expected,
        )


class TestSetGraphicTag(unittest.TestCase):
    "tests for block.set_graphic_tag()"

    def test_set_graphic_tag(self):
        "create graphic tag for a fig"
        # register XML namespaces
        xmlio.register_xmlns()
        xml_string = '<fig xmlns:xlink="http://www.w3.org/1999/xlink" />'
        tag = ElementTree.fromstring(xml_string)
        image_href = "image.png"
        new_file_name = "new_image.png"
        expected = (
            b'<fig xmlns:xlink="http://www.w3.org/1999/xlink">'
            b'<graphic mimetype="image" mime-subtype="png" xlink:href="new_image.png" />'
            b"</fig>"
        )
        block.set_graphic_tag(tag, image_href, new_file_name)
        self.assertEqual(ElementTree.tostring(tag), expected)


class TestSetCaptionTag(unittest.TestCase):
    "tests for block.set_caption_tag()"

    def test_set_caption_tag(self):
        "create caption tag for a fig"
        body_tag_xml_string = (
            b"<body>"
            b"<p>Title <italic>here</italic>. "
            b"Caption paragraph <italic>ici</italic>."
            b"</p>"
            b"</body>"
        )
        body_tag = ElementTree.fromstring(body_tag_xml_string)
        tag = Element("fig")
        caption_index = 0
        expected = (
            b"<fig>"
            b"<caption>"
            b"<title>Title <italic>here</italic>.</title>"
            b"<p>Caption paragraph <italic>ici</italic>.</p>"
            b"</caption>"
            b"</fig>"
        )
        block.set_caption_tag(tag, body_tag, caption_index)
        self.assertEqual(ElementTree.tostring(tag), expected)


class TestSubArticleTagParts(unittest.TestCase):
    "tests for block.sub_article_tag_parts()"

    def test_sub_article_tag_parts(self):
        "test parsing sub-article XML tag data"
        id_value = "sa0"
        xml_string = '<sub-article id="%s"><body/></sub-article>' % id_value
        sub_article_root = ElementTree.fromstring(xml_string)
        result = block.sub_article_tag_parts(sub_article_root)
        self.assertEqual(result[0], id_value)
        self.assertTrue(isinstance(result[1], Element))
        self.assertEqual(result[1].tag, "body")


class TestTagIndexGroups(unittest.TestCase):
    "tests for block.tag_index_groups()"

    def setUp(self):
        self.sub_article_id = "sa0"
        self.identifier = "test.zip"

    def test_tag_index_groups(self):
        "test body XML tag with fig content"
        xml_string = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<blockquote><p>Quotation.</p></blockquote>"
            "<p><bold>Author response image 1.</bold></p>"
            "<p>Caption title. Caption paragraph <italic>here</italic>.</p>"
            '<p><inline-graphic xlink:href="test.png"/></p>'
            "</body>"
        )
        block_type = "fig"
        expected = [{"label_index": 1, "caption_index": 2, "inline_graphic_index": 3}]
        body_tag = ElementTree.fromstring(xml_string)
        result = block.tag_index_groups(
            body_tag, self.sub_article_id, block_type, self.identifier
        )
        self.assertDictEqual(result[0], expected[0])

    def test_table_no_caption(self):
        "test body XML tag with a table and no caption"
        xml_string = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p><bold>Author response table 1.</bold></p>"
            '<p><inline-graphic xlink:href="test.png"/></p>'
            "</body>"
        )
        block_type = "table"
        expected = {"label_index": 0, "caption_index": False, "inline_graphic_index": 1}
        body_tag = ElementTree.fromstring(xml_string)
        result = block.tag_index_groups(
            body_tag, self.sub_article_id, block_type, self.identifier
        )
        self.assertDictEqual(result[0], expected)

    def test_empty_body_tag(self):
        "test body XML tag with no tags inside"
        xml_string = "<body></body>"
        block_type = "fig"
        expected = []
        body_tag = ElementTree.fromstring(xml_string)
        result = block.tag_index_groups(
            body_tag, self.sub_article_id, block_type, self.identifier
        )
        self.assertEqual(result, expected)


class TestTitleParagraphContent(unittest.TestCase):
    "tests for block.title_paragraph_content()"

    def test_title_paragraph_content(self):
        "a simple example of string parts"
        string_list = [
            "<p>Caption title.",
            " Caption paragraph.",
            "</p>",
        ]
        expected = ("<p>Caption title.", " Caption paragraph.</p>")
        result = block.title_paragraph_content(string_list)
        self.assertEqual(result, expected)

    def test_multiple_sentences(self):
        "a simple example of string parts"
        string_list = [
            "<p>A title.",
            " A caption paragraph.",
            " Another paragraph.",
            "</p>",
        ]
        expected = ("<p>A title.", " A caption paragraph. Another paragraph.</p>")
        result = block.title_paragraph_content(string_list)
        self.assertEqual(result, expected)

    def test_italic(self):
        "test where an unmatched inline formatting tag is repaired"
        string_list = [
            "<p>The title<bold>.",
            "</bold> Another <bold>bold term</bold>.",
            " Another paragraph.",
            "</p>",
        ]
        expected = (
            "<p>The title<bold>.</bold> Another <bold>bold term</bold>.",
            " Another paragraph.</p>",
        )
        result = block.title_paragraph_content(string_list)
        self.assertEqual(result, expected)

    def test_empty_list(self):
        "test an empty list"
        string_list = [""]
        expected = ("", None)
        result = block.title_paragraph_content(string_list)
        self.assertEqual(result, expected)


class TestCaptionTitleParagraph(unittest.TestCase):
    "tests for block.caption_title_paragraph()"

    def setUp(self):
        # register XML namespaces
        xmlio.register_xmlns()

    def test_simple_title(self):
        "test a simple example"
        xml_string = "<p>Title. Caption.</p>"
        tag = ElementTree.fromstring(xml_string)
        caption_title_p_tag, caption_paragraph_p_tag = block.caption_title_paragraph(
            tag
        )
        self.assertEqual(ElementTree.tostring(caption_title_p_tag), b"<p>Title.</p>")
        self.assertEqual(
            ElementTree.tostring(caption_paragraph_p_tag), b"<p>Caption.</p>"
        )

    def test_organism_title(self):
        "test for italic tag included"
        xml_string = "<p>In <italic>B. subtilis</italic>, the title. Caption.</p>"
        tag = ElementTree.fromstring(xml_string)
        caption_title_p_tag, caption_paragraph_p_tag = block.caption_title_paragraph(
            tag
        )
        self.assertEqual(
            ElementTree.tostring(caption_title_p_tag),
            b"<p>In <italic>B. subtilis</italic>, the title.</p>",
        )
        self.assertEqual(
            ElementTree.tostring(caption_paragraph_p_tag), b"<p>Caption.</p>"
        )

    def test_two_bold_tags(self):
        "edge case with more than one bold tag and second one is around the title full stop"
        xml_string = (
            "<p>The title<bold>.</bold> Another <bold>bold term</bold>."
            " Another paragraph.</p>"
        )
        tag = ElementTree.fromstring(xml_string)
        caption_title_p_tag, caption_paragraph_p_tag = block.caption_title_paragraph(
            tag
        )
        self.assertEqual(
            ElementTree.tostring(caption_title_p_tag),
            b"<p>The title<bold>.</bold> Another <bold>bold term</bold>.</p>",
        )
        self.assertEqual(
            ElementTree.tostring(caption_paragraph_p_tag), b"<p>Another paragraph.</p>"
        )

    def test_ext_link_tag(self):
        "edge case with an ext-link tag in the title and challenging full stop separations"
        xml_string = '<p xmlns:xlink="http://www.w3.org/1999/xlink">(Figure 2A from <ext-link ext-link-type="uri" xlink:href="https://example.org/one/two">(Anonymous et al., 2011)</ext-link>)<bold>.</bold> Comparison of Tests against Γ ( 4,5) (a = 0.05). The normality tests used were severely underpowered for n&lt;100 (<ext-link ext-link-type="uri" xlink:href="https://example.org/one/two">(Anonymous et al., 2011)</ext-link>).</p>'
        tag = ElementTree.fromstring(xml_string)
        caption_title_p_tag, caption_paragraph_p_tag = block.caption_title_paragraph(
            tag
        )
        self.assertEqual(
            ElementTree.tostring(caption_title_p_tag),
            b'<p xmlns:xlink="http://www.w3.org/1999/xlink">(Figure 2A from <ext-link ext-link-type="uri" xlink:href="https://example.org/one/two">(Anonymous et al., 2011)</ext-link>)<bold>.</bold> Comparison of Tests against &#915; ( 4,5) (a = 0.</p>',
        )
        self.assertEqual(
            ElementTree.tostring(caption_paragraph_p_tag),
            b'<p xmlns:xlink="http://www.w3.org/1999/xlink">05). The normality tests used were severely underpowered for n&lt;100 (<ext-link ext-link-type="uri" xlink:href="https://example.org/one/two">(Anonymous et al., 2011)</ext-link>).</p>',
        )

    def test_mml_tag(self):
        "edge case where a full stop in math formula should not be used as separate parts"
        xml_string = '<p xmlns:mml="http://www.w3.org/1998/Math/MathML">For one participant <inline-formula><mml:math alttext="" display="inline"><mml:mspace width="0.222em" /></mml:math></inline-formula> is a formula.</p>'
        tag = ElementTree.fromstring(xml_string)
        caption_title_p_tag, caption_paragraph_p_tag = block.caption_title_paragraph(
            tag
        )
        self.assertEqual(
            ElementTree.tostring(caption_title_p_tag),
            b'<p xmlns:mml="http://www.w3.org/1998/Math/MathML">For one participant <inline-formula><mml:math alttext="" display="inline"><mml:mspace width="0.222em" /></mml:math></inline-formula> is a formula.</p>',
        )
        self.assertEqual(ElementTree.tostring(caption_paragraph_p_tag), b"<p />")


class TestSplitTtitleParts(unittest.TestCase):
    "tests for block.split_title_parts()"

    def test_split_title_parts(self):
        "test spliting a simple example"
        xml_string = "<p>A title. A caption paragraph.</p>"
        expected = ["<p>A title.", " A caption paragraph.", "</p>"]
        result = block.split_title_parts(xml_string)
        self.assertEqual(result, expected)

    def test_multiple_sentences(self):
        "test spliting a simple example"
        xml_string = "<p>A title. A caption paragraph. Another paragraph.</p>"
        expected = [
            "<p>A title.",
            " A caption paragraph.",
            " Another paragraph.",
            "</p>",
        ]
        result = block.split_title_parts(xml_string)
        self.assertEqual(result, expected)

    def test_namespace(self):
        "test spliting a simple example"
        xml_string = (
            '<p xmlns:xlink="http://www.w3.org/1999/xlink">'
            'A title only (<ext-link xlink:href="http://example.org"/>).'
            "</p>"
        )
        expected = [
            '<p xmlns:xlink="http://www.w3.org/1999/xlink">A title only (<ext-link '
            'xlink:href="http://example.org"/>).',
            "</p>",
        ]
        result = block.split_title_parts(xml_string)
        self.assertEqual(result, expected)

    def test_unmatched_tags(self):
        "example where there are unmatched tags in the result"
        xml_string = xml_string = (
            "<p>The title<bold>.</bold> Another <bold>bold term</bold>."
            " Another paragraph.</p>"
        )
        expected = [
            "<p>The title<bold>.",
            "</bold> Another <bold>bold term</bold>.",
            " Another paragraph.",
            "</p>",
        ]
        result = block.split_title_parts(xml_string)
        self.assertEqual(result, expected)

    def test_blank_string(self):
        "test splitting a blank string"
        xml_string = ""
        expected = []
        result = block.split_title_parts(xml_string)
        self.assertEqual(result, expected)

    def test_no_full_stop(self):
        "test splitting string wiht no full stop"
        xml_string = "<p>Test</p>"
        expected = ["<p>Test</p>"]
        result = block.split_title_parts(xml_string)
        self.assertEqual(result, expected)


class TestStripTagText(unittest.TestCase):
    "tests for block.strip_tag_text()"

    def test_strip_tag_text(self):
        "test an example with whitespace to the left of the tag"
        xml_string = b"<p> <inline-graphic /> </p>"
        expected = b"<p><inline-graphic /> </p>"
        p_tag = ElementTree.fromstring(xml_string)
        block.strip_tag_text(p_tag)
        self.assertEqual(ElementTree.tostring(p_tag), expected)

    def test_non_element(self):
        "test if the input is not a tag"
        tag = "foo"
        self.assertEqual(block.strip_tag_text(tag), None)


class TestStripTagTail(unittest.TestCase):
    "tests for block.strip_tag_tail()"

    def test_strip_tag_tail(self):
        "test an example with whitespace to the left and right of the tag"
        xml_string = b"<p> <inline-graphic /> </p>"
        expected = b"<inline-graphic />"
        p_tag = ElementTree.fromstring(xml_string)
        inline_graphic_tag = p_tag.find("inline-graphic")
        block.strip_tag_tail(inline_graphic_tag)
        self.assertEqual(ElementTree.tostring(inline_graphic_tag), expected)

    def test_non_element(self):
        "test if the input is not a tag"
        tag = "foo"
        self.assertEqual(block.strip_tag_tail(tag), None)


class TestInlineGraphicTagFromTag(unittest.TestCase):
    "tests for block.inline_graphic_tag_from_tag()"

    def test_tag_found(self):
        "test getting a inline-graphic tag from a p tag"
        xml_string = b"<p>   <inline-graphic />   </p>"
        tag = ElementTree.fromstring(xml_string)
        expected = b"<inline-graphic />"
        result = block.inline_graphic_tag_from_tag(tag)
        self.assertEqual(ElementTree.tostring(result), expected)


class TestSetLabelTag(unittest.TestCase):
    "tests for block.set_label_tag()"

    def test_set_label_tag(self):
        "create label tag for a fig"
        body_tag_xml_string = b"<body><p><bold>Label</bold></p></body>"
        body_tag = ElementTree.fromstring(body_tag_xml_string)
        tag = Element("fig")
        label_index = 0
        expected = b"<fig><label>Label</label></fig>"
        block.set_label_tag(tag, body_tag, label_index)
        self.assertEqual(ElementTree.tostring(tag), expected)
