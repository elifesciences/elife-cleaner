import unittest
from elifecleaner import utils


class TestPadMsid(unittest.TestCase):
    def test_pad_msid(self):
        self.assertEqual(utils.pad_msid(666), "00666")
        self.assertEqual(utils.pad_msid("666"), "00666")


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
