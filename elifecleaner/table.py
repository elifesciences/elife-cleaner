import csv
from io import StringIO
from xml.etree.ElementTree import Element, SubElement
from jatsgenerator.utils import append_to_tag
from elifecleaner import block, utils


def table_wrap_id(sub_article_id, table_index):
    "create an id attribute for a table-wrap tag"
    return "%stable%s" % (sub_article_id, table_index)


def table_tag_index_groups(body_tag, sub_article_id, identifier):
    "iterate through the tags in body_tag and find groups of tags to be converted to a table-wrap"
    return block.tag_index_groups(body_tag, sub_article_id, "table", identifier)


def transform_table_group(body_tag, table_index, table_group, sub_article_id):
    "transform one set of p tags into table-wrap tags as specified in the table_group dict"
    inline_graphic_p_tag = body_tag[table_group.get("inline_graphic_index")]
    inline_graphic_tag = block.inline_graphic_tag_from_tag(inline_graphic_p_tag)
    image_href = utils.xlink_href(inline_graphic_tag)

    # insert tags into original inline-graphic
    block.set_label_tag(inline_graphic_p_tag, body_tag, table_group.get("label_index"))

    # caption
    if table_group.get("caption_index"):
        block.set_caption_tag(
            inline_graphic_p_tag, body_tag, table_group.get("caption_index")
        )

    # graphic tag
    new_file_name = image_href
    block.set_graphic_tag(inline_graphic_p_tag, image_href, new_file_name)

    # convert inline-graphic p tag to a table-wrap tag
    inline_graphic_p_tag.tag = "table-wrap"
    inline_graphic_p_tag.set("id", table_wrap_id(sub_article_id, table_index))

    # delete the old inline-graphic tag
    inline_graphic_p_tag.remove(inline_graphic_tag)

    # remove the old p tags
    if table_group.get("caption_index"):
        del body_tag[table_group.get("caption_index")]
    del body_tag[table_group.get("label_index")]


def transform_table_groups(body_tag, table_index_groups, sub_article_id):
    "transform p tags in the body_tag to table-wrap tags as listed in table_index_groups"
    # transform the table tags in reverse order
    table_index = len(table_index_groups)
    for table_group in reversed(table_index_groups):
        transform_table_group(body_tag, table_index, table_group, sub_article_id)
        # decrement the index
        table_index -= 1


def transform_table(sub_article_root, identifier):
    "transform inline-graphic tags and related p tags into a table-wrap tag"
    sub_article_id, body_tag = block.sub_article_tag_parts(sub_article_root)
    if body_tag is not None:
        # match paragraphs with data in them and record the tag indexes
        table_index_groups = table_tag_index_groups(
            body_tag, sub_article_id, identifier
        )
        transform_table_groups(body_tag, table_index_groups, sub_article_id)
    return sub_article_root


def tsv_to_list(tsv_string):
    "convert Tab Separated Value (TSV) string to a list"
    table_rows = []
    reader = csv.reader(StringIO(tsv_string), delimiter="\t")
    for row in reader:
        table_rows.append(row)
    return table_rows


def list_to_table_xml(table_rows):
    "convert list of rows into table XML"
    table_tag = Element("table")
    for row_index, row in enumerate(table_rows):
        if row_index <= 0:
            block_tag = SubElement(table_tag, "thead")
            cell_tag_name = "th"
        elif row_index == 1:
            block_tag = SubElement(table_tag, "tbody")
            cell_tag_name = "td"
        tr_tag = SubElement(block_tag, "tr")
        for cell in row:
            # replace new line charactes with a break tag
            cell = cell.replace("\n", "<break/>")
            # strip whitespace
            cell = cell.lstrip().rstrip()
            # append to the tr tag
            append_to_tag(tr_tag, cell_tag_name, cell)
    return table_tag
