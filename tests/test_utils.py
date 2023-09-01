import unittest
from xml.etree import ElementTree
from elifecleaner import utils


class TestPadMsid(unittest.TestCase):
    def test_pad_msid(self):
        self.assertEqual(utils.pad_msid(666), "00666")
        self.assertEqual(utils.pad_msid("666"), "00666")


class TestFileExtension(unittest.TestCase):
    def test_file_extension(self):
        passes = [(None, None), ("elife-70493-sa1-fig1.png", "png")]
        for file_name, expected in passes:
            self.assertEqual(
                utils.file_extension(file_name),
                expected,
            )


class TestMatchControlCharacterEntities(unittest.TestCase):
    def test_match_control_character_entities(self):
        self.assertEqual([], utils.match_control_character_entities(""))
        self.assertEqual(
            ["&#x001C;"], utils.match_control_character_entities("&#x001C;")
        )
        self.assertEqual(
            ["&#x001C;"], utils.match_control_character_entities("aaaa&#x001C;--")
        )
        self.assertEqual(
            ["&#x001E;", "&#x001E;"],
            utils.match_control_character_entities(" &#x001E;--&#x001E;"),
        )


class TestReplaceControlCharacterEntities(unittest.TestCase):
    def test_replace_control_character_entities(self):
        # empty string
        self.assertEqual("", utils.replace_control_character_entities(""))
        # one entity
        self.assertEqual(
            utils.CONTROL_CHARACTER_ENTITY_REPLACEMENT,
            utils.replace_control_character_entities("&#x001C;"),
        )
        # multiple entities
        self.assertEqual(
            utils.CONTROL_CHARACTER_ENTITY_REPLACEMENT * 4,
            utils.replace_control_character_entities("&#x00;&#x001C;&#x001D;&#x001E;"),
        )
        # entity found inside a string
        string_base = "<title>To %snd odd entities.</title>"
        string = string_base % "&#x001D;"
        expected = string_base % utils.CONTROL_CHARACTER_ENTITY_REPLACEMENT
        self.assertEqual(expected, utils.replace_control_character_entities(string))


class TestXlinkHref(unittest.TestCase):
    def test_xlink_href(self):
        image_href = "image.png"
        xml_string = (
            '<inline-graphic xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="%s"/>'
        ) % image_href
        href = utils.xlink_href(ElementTree.fromstring(xml_string))
        self.assertEqual(href, image_href)


class TestOpenTag(unittest.TestCase):
    def test_open_tag(self):
        tag_name = "italic"
        expected = "<italic>"
        self.assertEqual(utils.open_tag(tag_name), expected)

    def test_open_tag_with_attr(self):
        tag_name = "xref"
        attr = {"id": "sa2fig1", "ref-type": "fig"}
        expected = '<xref id="sa2fig1" ref-type="fig">'
        self.assertEqual(utils.open_tag(tag_name, attr), expected)


class TestRemoveTags(unittest.TestCase):
    "tests for utils.remove_tags()"

    def test_remove_tags(self):
        xml_string = "<root><hr/></root>"
        expected = b"<root />"
        xml_root = ElementTree.fromstring(xml_string)
        result = utils.remove_tags(xml_root, "hr")
        self.assertEqual(ElementTree.tostring(result), expected)

    def test_complicated_remove_tags(self):
        xml_string = "<root><hr/><p><hr/></p></root>"
        expected = b"<root><p /></root>"
        xml_root = ElementTree.fromstring(xml_string)
        result = utils.remove_tags(xml_root, "hr")
        self.assertEqual(ElementTree.tostring(result), expected)
