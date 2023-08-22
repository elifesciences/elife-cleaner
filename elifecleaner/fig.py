from xml.etree.ElementTree import Element
from elifecleaner import block, utils


def inf_file_identifier(inf_file_name):
    "specific part of an inline graphic file name, e.g. inf1 in elife-70493-inf1.png"
    return inf_file_name.rsplit(".", 1)[0].rsplit("-", 1)[-1]


def fig_file_name_identifier(sub_article_id, fig_index):
    "create the unique portion of a fig file name"
    return "%s-fig%s" % (sub_article_id, fig_index)


def fig_id(sub_article_id, fig_index):
    "create an id attribute for a fig tag"
    return "%sfig%s" % (sub_article_id, fig_index)


def fig_file_name(inf_file_name, sub_article_id, fig_index):
    "from inf file name create a new fig file name"
    return inf_file_name.replace(
        inf_file_identifier(inf_file_name), "%s-fig%s" % (sub_article_id, fig_index)
    )


def fig_tag_index_groups(body_tag, sub_article_id, identifier):
    "iterate through the tags in body_tag and find groups of tags to be converted to a fig"
    return block.tag_index_groups(body_tag, sub_article_id, "fig", identifier)


def remove_tag_attributes(tag):
    "remove attributes from the tag"
    if not isinstance(tag, Element):
        return
    attribute_names = [name for name in tag.attrib]
    for attrib_name in attribute_names:
        del tag.attrib[attrib_name]


def inline_graphic_hrefs(sub_article_root, identifier):
    "get inline-graphic href values"
    sub_article_id, body_tag = block.sub_article_tag_parts(sub_article_root)
    href_list = []
    if body_tag is not None:
        # match paragraphs with fig data in them and record the tag indexes
        fig_index_groups = fig_tag_index_groups(body_tag, sub_article_id, identifier)
        for group in fig_index_groups:
            if group.get("inline_graphic_index"):
                inline_graphic_p = body_tag[group.get("inline_graphic_index")]
                inline_graphic_tag = block.inline_graphic_tag_from_tag(inline_graphic_p)
                image_href = utils.xlink_href(inline_graphic_tag)
                if image_href:
                    href_list.append(image_href)
    return href_list


def graphic_hrefs(sub_article_root, identifier):
    "get graphic href values"
    sub_article_id, body_tag = block.sub_article_tag_parts(sub_article_root)
    href_list = []
    if body_tag is not None:
        for graphic_tag in body_tag.findall(".//graphic"):
            image_href = utils.xlink_href(graphic_tag)
            if image_href:
                href_list.append(image_href)
    return href_list


def transform_fig_group(body_tag, fig_index, fig_group, sub_article_id):
    "transform one set of p tags into fig tags as specified in the fig_group dict"
    inline_graphic_p_tag = body_tag[fig_group.get("inline_graphic_index")]
    inline_graphic_tag = block.inline_graphic_tag_from_tag(inline_graphic_p_tag)
    image_href = utils.xlink_href(inline_graphic_tag)

    # insert tags into original inline-graphic
    block.set_label_tag(inline_graphic_p_tag, body_tag, fig_group.get("label_index"))

    # caption
    if fig_group.get("caption_index"):
        block.set_caption_tag(
            inline_graphic_p_tag, body_tag, fig_group.get("caption_index")
        )

    # rename the image file
    new_file_name = fig_file_name(image_href, sub_article_id, fig_index)

    # graphic tag
    block.set_graphic_tag(inline_graphic_p_tag, image_href, new_file_name)

    # convert inline-graphic p tag to a fig tag and remove attributes
    inline_graphic_p_tag.tag = "fig"
    inline_graphic_p_tag.set("id", fig_id(sub_article_id, fig_index))

    # delete the old inline-graphic tag
    inline_graphic_p_tag.remove(inline_graphic_tag)

    # remove the old p tags
    if fig_group.get("caption_index"):
        del body_tag[fig_group.get("caption_index")]
    del body_tag[fig_group.get("label_index")]


def transform_fig_groups(body_tag, fig_index_groups, sub_article_id):
    "transform p tags in the body_tag to fig tags as listed in fig_index_groups"
    # transform the fig tags in reverse order
    fig_index = len(fig_index_groups)
    for fig_group in reversed(fig_index_groups):
        transform_fig_group(body_tag, fig_index, fig_group, sub_article_id)
        # decrement the fig index
        fig_index -= 1


def transform_fig(sub_article_root, identifier):
    "transform inline-graphic tags and related p tags into a fig tag"
    sub_article_id, body_tag = block.sub_article_tag_parts(sub_article_root)
    if body_tag is not None:
        # match paragraphs with fig data in them and record the tag indexes
        fig_index_groups = fig_tag_index_groups(body_tag, sub_article_id, identifier)
        transform_fig_groups(body_tag, fig_index_groups, sub_article_id)
    return sub_article_root
