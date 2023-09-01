import re


def pad_msid(msid):
    "zerofill string for article_id value"
    return "{:05d}".format(int(msid))


def file_extension(file_name):
    "parse file extension from file name"
    if not file_name:
        return None
    return file_name.rsplit(".", 1)[-1]


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


def match_control_characters(string):
    "search the string for XML-incompatible control characters"
    # char 9 is newline, 10 is tab, 13 is carriage return
    allowed = [9, 10, 13]
    return [char for char in string[:] if ord(char) <= 31 and ord(char) not in allowed]


def replace_control_characters(string):
    "replace control characters in the string"
    for char in list(set(match_control_characters(string))):
        string = string.replace(char, CONTROL_CHARACTER_ENTITY_REPLACEMENT)
    return string


def xlink_href(tag):
    "return the xlink:href attribute of the tag"
    return tag.get("{http://www.w3.org/1999/xlink}href")


def open_tag(tag_name, attr=None):
    "XML string for an open tag"
    if not attr:
        return "<%s>" % tag_name
    attr_values = []
    for name, value in sorted(attr.items()):
        attr_values.append('%s="%s"' % (name, value))
    return "<%s %s>" % (tag_name, " ".join(attr_values))


def close_tag(tag_name):
    "XML string for a close tag"
    return "</%s>" % tag_name


NAMESPACE_MAP = {
    "xmlns:mml": "http://www.w3.org/1998/Math/MathML",
    "xmlns:xlink": "http://www.w3.org/1999/xlink",
}


def namespace_string():
    "return a string of XML namespaces"
    return " ".join(
        [
            '%s="%s"' % (attrib_name, attrib_value)
            for attrib_name, attrib_value in NAMESPACE_MAP.items()
        ]
    )


def remove_tags(xml_root, tag_name):
    "remove tags with name tag_name from ElementTree"
    for tag_parent in xml_root.findall(".//%s/.." % tag_name):
        for tag in tag_parent.findall(tag_name):
            tag_parent.remove(tag)
    return xml_root
