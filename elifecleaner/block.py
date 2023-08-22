import re
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from elifecleaner import LOGGER, utils


FIG_LABEL_CONTENT_PATTERN = r"[A-Za-z ]+ image [0-9]+?\.{0,1}"


def match_fig_label_content(content):
    "check if the content is a label for a figure"
    return bool(re.match(FIG_LABEL_CONTENT_PATTERN, content)) if content else False


TABLE_LABEL_CONTENT_PATTERN = r"[A-Za-z ]+ table [0-9]+?\.{0,1}"


def match_table_label_content(content):
    "check if the content is a label for a table"
    return bool(re.match(TABLE_LABEL_CONTENT_PATTERN, content)) if content else False


def is_p_label(tag, sub_article_id, p_tag_index, block_type, identifier):
    "check if the p tag contents is a label"
    label = None
    if tag.find("bold") is not None:
        label = tag.find("bold").text
        LOGGER.info(
            '%s potential label "%s" in p tag %s of id %s',
            identifier,
            label,
            p_tag_index,
            sub_article_id,
        )
    if block_type == "fig":
        return match_fig_label_content(label)
    elif block_type == "table":
        return match_table_label_content(label)
    return None


def is_p_inline_graphic(tag, sub_article_id, p_tag_index, identifier):
    "check if the p tag contains only an inline-graphic tag"
    # simple check for a tag first
    if tag.find("inline-graphic") is None:
        LOGGER.info(
            "%s no inline-graphic tag found in p tag %s of id %s",
            identifier,
            p_tag_index,
            sub_article_id,
        )
        return False
    # check if the p tag contains an inline-grpahic only, ignoring whitespace
    if (
        tag.find("inline-graphic") is not None
        and (not tag.text or not tag.text.rstrip())
        and (
            not tag.find("inline-graphic").tail
            or not tag.find("inline-graphic").tail.rstrip()
        )
    ):
        LOGGER.info(
            "%s only inline-graphic tag found in p tag %s of id %s",
            identifier,
            p_tag_index,
            sub_article_id,
        )
        return True
    # default return None
    return None


def sub_article_tag_parts(sub_article_root):
    "return the id and body tag from a sub-article tag"
    sub_article_id = sub_article_root.get("id")
    body_tag = sub_article_root.find("body")
    return sub_article_id, body_tag


def tag_index_groups(body_tag, sub_article_id, block_type, identifier):
    "iterate through the tags in body_tag and find groups of tags to be converted to a fig"
    fig_index_groups = []
    if not body_tag:
        return fig_index_groups
    label_index = None
    caption_index = None
    for tag_index, child_tag in enumerate(body_tag.iterfind("*")):
        if child_tag.tag == "p":
            if label_index is None:
                # match figure label
                if is_p_label(
                    child_tag, sub_article_id, tag_index, block_type, identifier
                ):
                    label_index = tag_index
                    LOGGER.info(
                        "%s label p tag index %s of id %s",
                        identifier,
                        label_index,
                        sub_article_id,
                    )
            elif label_index is not None and caption_index is None:
                # look for optional caption
                if not is_p_inline_graphic(
                    child_tag, sub_article_id, tag_index, identifier
                ):
                    caption_index = tag_index
                    # loop to the next p tag
                    continue
                # if no caption found, check this p tag for an inline-graphic below
                caption_index = False
            if label_index is not None and caption_index is not None:
                # look for inline graphic to be converted to fig
                if is_p_inline_graphic(
                    child_tag, sub_article_id, tag_index, identifier
                ):
                    # add to the fig index group
                    fig_p_data = {
                        "label_index": label_index,
                        "caption_index": caption_index,
                        "inline_graphic_index": tag_index,
                    }
                    fig_index_groups.append(fig_p_data)
                # reset the indexes
                label_index = None
                caption_index = None
        else:
            # if is not a p tag, reset the indexes
            label_index = None
            caption_index = None
    return fig_index_groups


def title_paragraph_content(string_list):
    "from list of strings repair inline formatting tags and split into title and paragraph"
    # check for nested inline formatting tags
    title_content = ""
    content_remainders = []
    for title_part in string_list:
        if not title_content:
            title_content += title_part
            continue
        open_tag_count = title_content.count(utils.open_tag("italic"))
        close_tag_count = title_content.count(utils.close_tag("italic"))
        open_bold_tag_count = title_content.count(utils.open_tag("bold"))
        close_bold_tag_count = title_content.count(utils.close_tag("bold"))
        open_ext_link_tag_count = title_content.count(
            utils.open_tag("ext-link").rstrip(">")
        )
        close_ext_link_tag_count = title_content.count(utils.close_tag("ext-link"))
        if (
            open_tag_count != close_tag_count
            or open_bold_tag_count != close_bold_tag_count
            or open_ext_link_tag_count != close_ext_link_tag_count
        ):
            title_content += title_part
        else:
            content_remainders.append(title_part)
    title_content = title_content.lstrip()
    paragraph_content = None
    if content_remainders:
        paragraph_content = "".join(content_remainders)
    return title_content, paragraph_content


def set_graphic_tag(parent, image_href, new_file_name):
    "add a graphic tag to the parent"
    graphic_tag = SubElement(parent, "graphic")
    graphic_tag.set("mimetype", "image")
    graphic_tag.set("mime-subtype", utils.file_extension(image_href))
    graphic_tag.set("{http://www.w3.org/1999/xlink}href", new_file_name)


def caption_title_paragraph(tag):
    "split the content into title and optional paragraph for a fig caption"
    xml_string = ElementTree.tostring(tag)
    if isinstance(xml_string, bytes):
        xml_string = str(xml_string, encoding="utf-8")

    # split the string into parts
    string_list = split_title_parts(xml_string)

    title_content, paragraph_content = title_paragraph_content(string_list)

    # fix enclosing tags
    if paragraph_content:
        title_content = "%s</p>" % title_content
        paragraph_content = "<p %s>%s" % (
            utils.namespace_string(),
            paragraph_content.lstrip(),
        )
    # parse XML string back into an Element
    caption_title_p_tag = ElementTree.fromstring(title_content)
    caption_paragraph_p_tag = None
    if paragraph_content:
        caption_paragraph_p_tag = ElementTree.fromstring(paragraph_content)

    return caption_title_p_tag, caption_paragraph_p_tag


def set_caption_tag(parent, body_tag, caption_index):
    "add a caption tag to the parent"
    caption_tag = SubElement(parent, "caption")

    # split into title and p tag portions
    caption_title_p_tag, caption_paragraph_p_tag = caption_title_paragraph(
        body_tag[caption_index]
    )

    caption_title_tag = SubElement(caption_tag, "title")
    caption_title_tag.text = caption_title_p_tag.text
    # handle if there are child tags in the title
    for child_tag in caption_title_p_tag.iterfind("*"):
        caption_title_tag.append(child_tag)
        caption_title_tag.tail = caption_title_p_tag.tail
    if caption_paragraph_p_tag is not None and caption_paragraph_p_tag.text:
        caption_p_tag = SubElement(caption_tag, "p")
        caption_p_tag.text = caption_paragraph_p_tag.text
        # handle if there are child tags in the caption
        for child_tag in caption_paragraph_p_tag.iterfind("*"):
            caption_p_tag.append(child_tag)
            caption_p_tag.tail = caption_paragraph_p_tag.tail


def split_title_parts(xml_string):
    "split the XML string into parts to be processed by caption_title_paragraph()"
    title_parts = []
    tag_match_pattern = re.compile(r"(<.*?>)")
    match_tag_groups = tag_match_pattern.split(xml_string)
    string_part = ""
    for tag_group in match_tag_groups:
        if "." in tag_group and "<" not in tag_group:
            if tag_group == ".":
                dot_parts = ["."]
            else:
                dot_parts = tag_group.split(".")

            for dot_index, dot_part in enumerate(dot_parts):
                suffix = ""
                if dot_index + 1 < len(dot_parts):
                    suffix = "."
                string_part += "%s%s" % (dot_part, suffix)
                title_parts.append(string_part)
                string_part = ""
        else:
            string_part += tag_group
    # append the final content
    if title_parts:
        title_parts[-1] += string_part
    elif string_part:
        # only one string found
        title_parts.append(string_part)

    return title_parts


def strip_tag_text(tag):
    "remove whitespace to the left of the child tag if present"
    if isinstance(tag, Element) and tag.text is not None and not tag.text.rstrip():
        tag.text = None


def strip_tag_tail(tag):
    "remove whitespace to the right of the tag if present"
    if isinstance(tag, Element) and tag.tail is not None and not tag.tail.rstrip():
        tag.tail = None


def inline_graphic_tag_from_tag(tag):
    "get the inline-graphic tag from the parent tag"
    strip_tag_text(tag)
    inline_graphic_tag = tag.find("inline-graphic")
    strip_tag_tail(inline_graphic_tag)
    return inline_graphic_tag


def set_label_tag(parent, body_tag, label_index):
    "add a label tag to the parent"
    # insert tags into original inline-graphic
    label_tag = SubElement(parent, "label")
    # copy content from the label_index p tag
    label_tag.text = body_tag[label_index].find("bold").text
