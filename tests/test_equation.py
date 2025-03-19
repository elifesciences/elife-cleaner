import unittest
from xml.etree import ElementTree
from elifetools import xmlio
from elifecleaner import equation


class TestInlineFormulaGraphicHrefs(unittest.TestCase):
    "tests for equation.inline_formula_graphic_hrefs()"

    def test_graphic_hrefs(self):
        "get a list of xlink:href values from inline-formula inline-graphic"
        xml_string = (
            b'<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            b"<body>"
            b'<p>First paragraph with an inline equation <inline-formula id="sa1equ1">'
            b'<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            b"</inline-formula>.</p>"
            b"<p>Following is a display formula:</p>"
            b'<p><inline-graphic xlink:href="elife-inf2.jpg" /></p>'
            b"</body>"
            b"</sub-article>"
        )
        identifier = "test.zip"
        tag = ElementTree.fromstring(xml_string)
        expected = ["elife-sa1-equ1.jpg"]
        result = equation.inline_formula_graphic_hrefs(tag, identifier)
        self.assertEqual(result, expected)

    def test_graphic_hrefs_no_match(self):
        "empty list of xlink:href values when there is no matching tag"
        xml_string = (
            b'<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<body><p/></body>"
            b"</sub-article>"
        )
        identifier = "test.zip"
        tag = ElementTree.fromstring(xml_string)
        expected = []
        result = equation.inline_formula_graphic_hrefs(tag, identifier)
        self.assertEqual(result, expected)

    def test_multiple(self):
        "test collecting multiple inline-formula inline-graphic data"
        xml_string = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            "<body>"
            "<p>An inline equation"
            ' <inline-formula id="sa1equ1">'
            '<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            "</inline-formula>"
            " and another inline equation"
            ' <inline-formula id="sa1equ2">'
            '<inline-graphic xlink:href="elife-sa1-equ2.jpg" />'
            "</inline-formula>"
            ".</p>"
            "</body>"
            "</sub-article>"
        )
        identifier = "test.zip"
        tag = ElementTree.fromstring(xml_string)
        expected = ["elife-sa1-equ1.jpg", "elife-sa1-equ2.jpg"]
        result = equation.inline_formula_graphic_hrefs(tag, identifier)
        self.assertEqual(result, expected)


class TestTransformEquations(unittest.TestCase):
    "tests for transform_equations()"

    def test_transform_equations(self):
        "test converting inline-graphic tags to disp-formula"
        xmlio.register_xmlns()
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg" />.</p>'
            "<p>Following is a display formula:</p>"
            '<disp-formula id="sa1equ2">'
            '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ2.jpg" />'
            "</disp-formula>"
            "</body>"
            "</sub-article>"
        )
        # invoke
        result = equation.transform_equations(sub_article_root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf8"), expected)

    def test_hybrid(self):
        "test when inline-formula and inline-graphic tags are included"
        xmlio.register_xmlns()
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Inline equation"
            ' <inline-formula id="sa1equ1"><inline-graphic xlink:href="elife-95901-sa1-equ1.jpg"'
            ' mimetype="image" mime-subtype="jpeg"/>'
            "</inline-formula>.</p>"
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg" />.</p>'
            "<p>Inline equation"
            ' <inline-formula id="sa1equ1"><inline-graphic xlink:href="elife-95901-sa1-equ1.jpg"'
            ' mimetype="image" mime-subtype="jpeg" /></inline-formula>.</p>'
            "<p>Following is a display formula:</p>"
            '<disp-formula id="sa1equ3">'
            '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ3.jpg" />'
            "</disp-formula>"
            "</body>"
            "</sub-article>"
        )
        # invoke
        result = equation.transform_equations(sub_article_root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf8"), expected)


class TestExtraEquationCount(unittest.TestCase):
    "test for extra_equation_count()"

    def test_inline_graphic(self):
        parent_tag = ElementTree.fromstring(
            '<p xmlns:xlink="http://www.w3.org/1999/xlink">An inline equation'
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>'
            ' and another inline equation <inline-graphic xlink:href="elife-inf2.jpg"/>.</p>'
        )
        expected = 2
        # invoke
        result = equation.extra_equation_count(parent_tag)
        # assert
        self.assertEqual(result, expected)

    def test_inline_formula(self):
        "test counting equation and potential equation tags"
        parent_tag = ElementTree.fromstring(
            '<p xmlns:xlink="http://www.w3.org/1999/xlink">An inline equation'
            ' <inline-formula id="sa0equ1"><inline-graphic xlink:href="elife-95901-sa0-equ1.jpg"'
            ' mimetype="image" mime-subtype="jpeg"/>'
            "</inline-formula>"
            ' and another inline equation <inline-formula id="sa0equ2">'
            '<inline-graphic xlink:href="elife-95901-sa0-equ2.jpg" mimetype="image"'
            ' mime-subtype="jpeg"/'
            "></inline-formula>.</p>"
        )
        expected = 2
        # invoke
        result = equation.extra_equation_count(parent_tag)
        # assert
        self.assertEqual(result, expected)

    def test_disp_formula(self):
        "test counting equation and potential equation tags"
        parent_tag = ElementTree.fromstring(
            '<disp-formula id="sa1equ1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ1.jpg" />'
            "</disp-formula>"
        )
        expected = 1
        # invoke
        result = equation.extra_equation_count(parent_tag)
        # assert
        self.assertEqual(result, expected)


class TestDispFormulaTagIndexGroups(unittest.TestCase):
    "tests for disp_formula_tag_index_groups()"

    def test_disp_formula(self):
        "test finding XML to be converted to disp-formula"
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = [
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 2,
                "tag_index": 2,
            }
        ]
        # invoke
        result = equation.disp_formula_tag_index_groups(body_tag, identifier)
        # assert
        self.assertEqual(result, expected)

    def test_multiple(self):
        "test a sample with multiple inline-formula and disp-formula"
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>An inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>'
            ' and another inline equation <inline-graphic xlink:href="elife-inf2.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = [
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 2,
                "tag_index": 3,
            }
        ]
        # invoke
        result = equation.disp_formula_tag_index_groups(body_tag, identifier)
        # assert
        self.assertEqual(result, expected)

    def test_hybrid(self):
        "test with an inline-formula tag to count"
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>An inline equation"
            ' <inline-formula id="sa0equ1"><inline-graphic xlink:href="elife-95901-sa0-equ1.jpg"'
            ' mimetype="image" mime-subtype="jpeg"/>'
            "</inline-formula>"
            ' and another inline equation <inline-formula id="sa0equ2">'
            '<inline-graphic xlink:href="elife-95901-sa0-equ2.jpg" mimetype="image"'
            ' mime-subtype="jpeg"/'
            "></inline-formula>.</p>"
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = [
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 2,
                "tag_index": 3,
            },
        ]
        # invoke
        result = equation.disp_formula_tag_index_groups(body_tag, identifier)
        # assert
        self.assertEqual(result, expected)


class TestTransformDispFormulas(unittest.TestCase):
    "tests for transform_disp_formulas()"

    def test_transform_disp_formulas(self):
        "convert inline-graphic tags to disp-formula"
        xmlio.register_xmlns()
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf1.jpg"/></p>'
            "<p>Second display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
        )
        index_groups = [
            {
                "inline_graphic_index": 1,
                "tag_index": 1,
            },
            {
                "inline_graphic_index": 3,
                "tag_index": 2,
            },
        ]
        sub_article_id = "sa1"
        expected = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First display formula:</p>"
            '<disp-formula id="sa1equ1">'
            '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ1.jpg" />'
            "</disp-formula>"
            "<p>Second display formula:</p>"
            '<disp-formula id="sa1equ2">'
            '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ2.jpg" />'
            "</disp-formula>"
            "</body>"
        )
        # invoke
        equation.transform_disp_formulas(body_tag, index_groups, sub_article_id)
        # assert
        self.assertEqual(ElementTree.tostring(body_tag).decode("utf8"), expected)


class TestFormulaId(unittest.TestCase):
    "tests for formula_id()"

    def test_formula_id(self):
        "test generating an id for an XML formula or equation"
        sub_article_id = "sa1"
        index = 1
        expected = "sa1equ1"
        # invoke
        result = equation.formula_id(sub_article_id, index)
        # assert
        self.assertEqual(result, expected)


class TestFormulaFileName(unittest.TestCase):
    "tests for formula_file_name()"

    def test_formula_file_name(self):
        "test generating a file name for a equation or formula graphic"
        inf_file_name = "elife-95901-inf1.jpg"
        sub_article_id = "sa1"
        index = "1"
        expected = "elife-95901-sa1-equ1.jpg"
        # invoke
        result = equation.formula_file_name(inf_file_name, sub_article_id, index)
        # assert
        self.assertEqual(result, expected)


class TestTransformDispFormula(unittest.TestCase):
    "tests for transform_disp_formula()"

    def test_transform_disp_formula(self):
        "test converting a single inline-graphic p tag into disp-formula"
        xmlio.register_xmlns()
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf1.jpg"/></p>'
            "<p>Second display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
        )
        index = "2"
        group = {
            "inline_graphic_index": 3,
            "tag_index": 2,
        }
        sub_article_id = "sa1"
        expected = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf1.jpg" /></p>'
            "<p>Second display formula:</p>"
            '<disp-formula id="sa1equ2">'
            '<graphic mimetype="image" mime-subtype="jpg" xlink:href="elife-sa1-equ2.jpg" />'
            "</disp-formula>"
            "</body>"
        )
        # invoke
        equation.transform_disp_formula(body_tag, index, group, sub_article_id)
        # assert
        self.assertEqual(ElementTree.tostring(body_tag).decode("utf8"), expected)


class TestEquationInlineGraphicHrefs(unittest.TestCase):
    "tests for equation_inline_graphic_hrefs()"

    def test_equation_inline(self):
        "test collecting href values for disp-formula"
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = ["elife-inf2.jpg"]
        # invoke
        result = equation.equation_inline_graphic_hrefs(sub_article_root, identifier)
        # assert
        self.assertEqual(result, expected)


class TestFormulaGraphicHrefs(unittest.TestCase):
    "tests for equation.formula_graphic_hrefs()"

    def test_formula_graphic_hrefs(self):
        "get a list of xlink:href values from disp-formula graphic tags"
        xml_string = (
            b'<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink"><body>'
            b"<p>Following is a display formula:</p>\n"
            b'<disp-formula id="sa1equ1">\n'
            b'<graphic mimetype="image" mime-subtype="jpg"'
            b' xlink:href="elife-sa1-equ1.jpg"/>\n'
            b"</disp-formula>\n"
            b"</body></sub-article>"
        )
        identifier = "test.zip"
        tag = ElementTree.fromstring(xml_string)
        expected = ["elife-sa1-equ1.jpg"]
        result = equation.formula_graphic_hrefs(tag, identifier)
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
        result = equation.formula_graphic_hrefs(tag, identifier)
        self.assertEqual(result, expected)


class TestInlineEquationInlineGraphicHrefs(unittest.TestCase):
    "tests for inline_equation_inline_graphic_hrefs()"

    def test_inline_equation_inline(self):
        "test collecting href values for inline-formula"
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = ["elife-inf1.jpg"]
        # invoke
        result = equation.inline_equation_inline_graphic_hrefs(
            sub_article_root, identifier
        )
        # assert
        self.assertEqual(result, expected)


class TestTransformInlineEquations(unittest.TestCase):
    "tests for transform_inline_equations()"

    def test_transform_inline_equations(self):
        "test converting inline-graphic tags to inline-formula"
        xmlio.register_xmlns()
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            "<body>"
            '<p>First paragraph with an inline equation <inline-formula id="sa1equ1">'
            '<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            "</inline-formula>.</p>"
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg" /></p>'
            "</body>"
            "</sub-article>"
        )
        # invoke
        result = equation.transform_inline_equations(sub_article_root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf8"), expected)

    def test_transform_multiple(self):
        "test converting multiple inline-graphic tags to inline-formula"
        xmlio.register_xmlns()
        sub_article_root = ElementTree.fromstring(
            '<sub-article id="sa1" xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<body>"
            "<p>An inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>'
            ' and another inline equation <inline-graphic xlink:href="elife-inf2.jpg"/>.</p>'
            "</body>"
            "</sub-article>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" id="sa1">'
            "<body>"
            "<p>An inline equation"
            ' <inline-formula id="sa1equ1">'
            '<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            "</inline-formula>"
            " and another inline equation"
            ' <inline-formula id="sa1equ2">'
            '<inline-graphic xlink:href="elife-sa1-equ2.jpg" />'
            "</inline-formula>"
            ".</p>"
            "</body>"
            "</sub-article>"
        )
        # invoke
        result = equation.transform_inline_equations(sub_article_root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf8"), expected)


class TestInlineFormulaTagIndexGroups(unittest.TestCase):
    "tests for inline_formula_tag_index_groups()"

    def test_inline_formula(self):
        "test finding XML to be converted to inline-formula"
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = [
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 0,
                "tag_index": 1,
            }
        ]
        # invoke
        result = equation.inline_formula_tag_index_groups(body_tag, identifier)
        # assert
        self.assertEqual(result, expected)

    def test_multiple(self):
        "test multiple inline-graphic tags in a p tag to be converted to inline-formula"
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>An inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>'
            ' and another inline equation <inline-graphic xlink:href="elife-inf2.jpg"/>.</p>'
            "</body>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = [
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 0,
                "tag_index": 1,
            },
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 0,
                "tag_index": 2,
            },
        ]
        # invoke
        result = equation.inline_formula_tag_index_groups(body_tag, identifier)
        # assert
        self.assertEqual(result, expected)

    def test_hybrid(self):
        "test with a converted disp-formula tag to count"
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<disp-formula id="sa0equ1"><graphic /></disp-formula>'
            "<p>An inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>'
            ' and another inline equation <inline-graphic xlink:href="elife-inf2.jpg"/>.</p>'
            "</body>"
        )
        identifier = "10.7554/eLife.95901.1"
        expected = [
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 1,
                "tag_index": 2,
            },
            {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": 1,
                "tag_index": 3,
            },
        ]
        # invoke
        result = equation.inline_formula_tag_index_groups(body_tag, identifier)
        # assert
        self.assertEqual(result, expected)


class TestTransformInlineFormulas(unittest.TestCase):
    "tests for transform_inline_formulas()"

    def test_transform_inline_formulas(self):
        "convert inline-graphic tags to inline-formula"
        xmlio.register_xmlns()
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First inline formula:"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/></p>'
            "<p>Second inline formula:"
            ' <inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
        )
        index_groups = [
            {
                "inline_graphic_index": 0,
                "tag_index": 1,
            },
            {
                "inline_graphic_index": 1,
                "tag_index": 2,
            },
        ]
        sub_article_id = "sa1"
        expected = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<p>First inline formula: <inline-formula id="sa1equ1">'
            '<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            "</inline-formula></p>"
            '<p>Second inline formula: <inline-formula id="sa1equ2">'
            '<inline-graphic xlink:href="elife-sa1-equ2.jpg" />'
            "</inline-formula></p>"
            "</body>"
        )
        # invoke
        equation.transform_inline_formulas(body_tag, index_groups, sub_article_id)
        # assert
        self.assertEqual(ElementTree.tostring(body_tag).decode("utf8"), expected)

    def test_multiple(self):
        "convert multiple inline-graphic tags in a p tag to inline-formula"
        xmlio.register_xmlns()
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>An inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>'
            ' and another inline equation <inline-graphic xlink:href="elife-inf2.jpg"/>.</p>'
            "</body>"
        )
        index_groups = [
            {
                "inline_graphic_index": 0,
                "tag_index": 1,
            },
            {
                "inline_graphic_index": 0,
                "tag_index": 2,
            },
        ]
        sub_article_id = "sa1"
        expected = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>An inline equation"
            ' <inline-formula id="sa1equ1">'
            '<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            "</inline-formula>"
            " and another inline equation"
            ' <inline-formula id="sa1equ2">'
            '<inline-graphic xlink:href="elife-sa1-equ2.jpg" />'
            "</inline-formula>"
            ".</p>"
            "</body>"
        )
        # invoke
        equation.transform_inline_formulas(body_tag, index_groups, sub_article_id)
        # assert
        self.assertEqual(ElementTree.tostring(body_tag).decode("utf8"), expected)


class TestTransformInlineFormula(unittest.TestCase):
    "tests for transform_inline_formula()"

    def test_transform_inline_formula(self):
        "test converting a single inline-graphic p tag into inline-formula"
        xmlio.register_xmlns()
        body_tag = ElementTree.fromstring(
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First inline formula:"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/></p>'
            "<p>Second inline formula:"
            ' <inline-graphic xlink:href="elife-inf2.jpg"/> and more text.</p>'
            "</body>"
        )
        index = "1"
        group = {
            "inline_graphic_index": 1,
            "tag_index": 2,
        }
        sub_article_id = "sa1"
        expected = (
            '<body xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<p>First inline formula:"
            ' <inline-graphic xlink:href="elife-inf1.jpg" /></p>'
            "<p>Second inline formula:"
            ' <inline-formula id="sa1equ1">'
            '<inline-graphic xlink:href="elife-sa1-equ1.jpg" />'
            "</inline-formula> and more text.</p>"
            "</body>"
        )
        # invoke
        equation.transform_inline_formula(body_tag, index, group, sub_article_id)
        # assert
        self.assertEqual(ElementTree.tostring(body_tag).decode("utf8"), expected)
