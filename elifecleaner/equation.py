from xml.etree.ElementTree import SubElement
from elifecleaner import block, utils
from elifecleaner.fig import remove_tag_attributes


def inline_formula_graphic_hrefs(sub_article_root, identifier):
    "return a list of inline-formula inline-graphic tag xlink:href values"
    body_tag = block.sub_article_tag_parts(sub_article_root)[1]
    current_hrefs = []
    if body_tag is not None:
        for graphic_tag in sub_article_root.findall(".//inline-formula/inline-graphic"):
            image_href = utils.xlink_href(graphic_tag)
            if image_href:
                current_hrefs.append(image_href)
    return current_hrefs


def transform_equations(sub_article_root, identifier):
    "transform inline-graphic tags into disp-formula tags"
    sub_article_id, body_tag = block.sub_article_tag_parts(sub_article_root)
    if body_tag is not None:
        # match paragraphs with data in them and record the tag indexes
        index_groups = disp_formula_tag_index_groups(body_tag, identifier)
        transform_disp_formulas(body_tag, index_groups, sub_article_id)
    return sub_article_root


def extra_equation_count(parent_tag):
    "count tags which are or may be converted to an equation"
    tag_count = 0
    if parent_tag.findall("inline-graphic"):
        # count the inline-graphic tags
        tag_count += len(parent_tag.findall("inline-graphic"))
    elif parent_tag.findall("inline-formula"):
        # count the inline-formula tags
        tag_count += len(parent_tag.findall("inline-formula"))
    elif parent_tag.tag == "disp-formula" and parent_tag.findall("graphic"):
        # count the block formula tags
        tag_count += len(parent_tag.findall("graphic"))
    return tag_count


def disp_formula_tag_index_groups(body_tag, identifier):
    "find p tags which have inline-graphic tags to convert to disp-formula"
    index_groups = []
    tag_id_index = 1
    for tag_index, parent_tag in enumerate(body_tag.iterfind("*")):
        # count the inline-graphic tags to get an id value
        if block.is_p_inline_graphic(
            tag=parent_tag,
            sub_article_id=None,
            p_tag_index=None,
            identifier=identifier,
        ):
            detail = {
                "label_index": None,
                "caption_index": None,
                "inline_graphic_index": tag_index,
                "tag_index": tag_id_index,
            }
            index_groups.append(detail)
            tag_id_index += 1
        tag_id_index += extra_equation_count(parent_tag)

    return index_groups


def transform_disp_formulas(body_tag, index_groups, sub_article_id):
    "transform p tags in the body_tag to disp-formula tags as listed in index_groups"
    for group in reversed(index_groups):
        index = group.get("tag_index")
        transform_disp_formula(body_tag, index, group, sub_article_id)


def formula_id(sub_article_id, index):
    "create an id attribute for a disp-formula tag"
    return "%sequ%s" % (sub_article_id, index)


def formula_file_name(inf_file_name, sub_article_id, index):
    "create a file name for an equation graphic file"
    return inf_file_name.replace(
        utils.inf_file_identifier(inf_file_name),
        "%s-equ%s" % (sub_article_id, index),
    )


def transform_disp_formula(body_tag, index, group, sub_article_id):
    "transform one set of p tags into disp-formula tags as specified in the group dict"
    inline_graphic_p_tag = body_tag[group.get("inline_graphic_index")]
    inline_graphic_tag = block.inline_graphic_tag_from_tag(inline_graphic_p_tag)
    image_href = utils.xlink_href(inline_graphic_tag)

    # rename the image file
    new_file_name = formula_file_name(image_href, sub_article_id, index)

    # graphic tag
    block.set_graphic_tag(inline_graphic_p_tag, image_href, new_file_name)

    # convert inline-graphic p tag and remove attributes
    inline_graphic_p_tag.tag = "disp-formula"
    inline_graphic_p_tag.set("id", formula_id(sub_article_id, index))

    # delete the old inline-graphic tag
    inline_graphic_p_tag.remove(inline_graphic_tag)


def equation_inline_graphic_hrefs(sub_article_root, identifier):
    "get inline-graphic xlink:href values to be disp-formula"
    body_tag = block.sub_article_tag_parts(sub_article_root)[1]
    href_list = []
    equation_index_groups = []
    if body_tag is not None:
        # find paragraphs to be disp-formula data
        equation_index_groups = disp_formula_tag_index_groups(body_tag, identifier)
        href_list = block.graphic_href_list(body_tag, equation_index_groups)
    return href_list


def formula_graphic_hrefs(sub_article_root, identifier):
    "get disp-formula graphic href values"
    sub_article_id, body_tag = block.sub_article_tag_parts(sub_article_root)
    href_list = []
    if body_tag is not None:
        for graphic_tag in body_tag.findall(".//disp-formula/graphic"):
            image_href = utils.xlink_href(graphic_tag)
            if image_href:
                href_list.append(image_href)
    return href_list


def inline_equation_inline_graphic_hrefs(sub_article_root, identifier):
    "get inline-graphic xlink:href values to be inline-formula"
    body_tag = block.sub_article_tag_parts(sub_article_root)[1]
    href_list = []
    equation_index_groups = []
    if body_tag is not None:
        # find paragraphs with inline-formula data in them and record the tag indexes
        equation_index_groups = inline_formula_tag_index_groups(body_tag, identifier)
        href_list = block.graphic_href_list(body_tag, equation_index_groups)
    return href_list


def transform_inline_equations(sub_article_root, identifier):
    "transform inline-graphic tags into inline-formula tags"
    sub_article_id, body_tag = block.sub_article_tag_parts(sub_article_root)
    if body_tag is not None:
        # match paragraphs with data in them and record the tag indexes
        index_groups = inline_formula_tag_index_groups(body_tag, identifier)
        transform_inline_formulas(body_tag, index_groups, sub_article_id)
    return sub_article_root


def inline_formula_tag_index_groups(body_tag, identifier):
    "find p tags which have inline-graphic tags to convert to inline-formula"
    index_groups = []
    tag_id_index = 1
    for tag_index, parent_tag in enumerate(body_tag.iterfind("*")):
        if parent_tag.find("inline-graphic") is not None and not (
            block.is_p_inline_graphic(
                tag=parent_tag,
                sub_article_id=None,
                p_tag_index=None,
                identifier=identifier,
            )
        ):
            for inline_graphic_tag in parent_tag.findall("inline-graphic"):
                detail = {
                    "label_index": None,
                    "caption_index": None,
                    "inline_graphic_index": tag_index,
                    "tag_index": tag_id_index,
                }

                index_groups.append(detail)
                tag_id_index += 1
        tag_id_index += extra_equation_count(parent_tag)

    return index_groups


def transform_inline_formulas(body_tag, index_groups, sub_article_id):
    "transform inline-graphic tags to inline-formula tags as listed in index_groups"
    for group in index_groups:
        index = group.get("tag_index")
        transform_inline_formula(body_tag, index, group, sub_article_id)


def transform_inline_formula(body_tag, index, group, sub_article_id):
    "transform one set of p tags into inline-formula tags as specified in the group dict"
    inline_graphic_p_tag = body_tag[group.get("inline_graphic_index")]
    inline_graphic_tag = block.inline_graphic_tag_from_tag(inline_graphic_p_tag)
    image_href = utils.xlink_href(inline_graphic_tag)

    # rename the inline-graphic tag to inline-formula
    remove_tag_attributes(inline_graphic_tag)
    inline_graphic_tag.tag = "inline-formula"
    inline_graphic_tag.set("id", formula_id(sub_article_id, index))

    # add inline-graphic tag
    new_inline_graphic_tag = SubElement(inline_graphic_tag, "inline-graphic")
    new_file_name = formula_file_name(image_href, sub_article_id, index)
    new_inline_graphic_tag.set("{http://www.w3.org/1999/xlink}href", new_file_name)
