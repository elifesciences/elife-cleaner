import re


def pad_msid(msid):
    "zerofill string for article_id value"
    return "{:05d}".format(int(msid))


# match ascii characters from decimal 0 to 31, as hexidecimal character entitiy strings
# e.g. &#x001D; or &#x01;
CONTROL_CHARACTER_ENTITY_MATCH_PATTERN = r"&#x0{0,2}[0-1][0-9A-Fa-f];"
# string to replace character entities with
CONTROL_CHARACTER_ENTITY_REPLACEMENT = "_____"


def match_control_character_entities(string):
    "search the string for character entities of XML-incompatible control characters"
    match_pattern = re.compile(CONTROL_CHARACTER_ENTITY_MATCH_PATTERN)
    return match_pattern.findall(string)


def replace_control_character_entities(string):
    "replace character entities of control characters in the string"
    match_pattern = re.compile(CONTROL_CHARACTER_ENTITY_MATCH_PATTERN)
    return match_pattern.sub(CONTROL_CHARACTER_ENTITY_REPLACEMENT, string)
