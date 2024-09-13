import copy
import re
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from elifearticle.article import Article, Contributor, Role
from docmaptools import parse as docmap_parse
from jatsgenerator import build
from elifecleaner import assessment_terms, LOGGER, parse, utils

XML_NAMESPACES = {
    "ali": "http://www.niso.org/schemas/ali/1.0/",
    "mml": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
}

# to replace docmap article type with sub-article article_type
ARTICLE_TYPE_MAP = {
    "evaluation-summary": "editor-report",
    "review-article": "referee-report",
    "reply": "author-comment",
}


def reorder_review_articles(content_list):
    "reorder content based on the article-title, if present"
    number_match = re.compile(rb".*<article-title>.*\s+#(\d+)\s+.*")
    content_to_sort = []
    for content in content_list:
        matches = number_match.match(content.get("xml"))
        if matches:
            content_map = {"num": int(matches[1]), "content": content}
        else:
            content_map = {"num": 0, "content": content}
        content_to_sort.append(content_map)
    sorted_content = sorted(content_to_sort, key=lambda item: item.get("num"))
    return [content_item.get("content") for content_item in sorted_content]


def reorder_content_json(content_json):
    "reorder the content list"
    # append lists of specific content types to make a new list
    content_json = (
        [
            content
            for content in content_json
            if content.get("type") == "evaluation-summary"
        ]
        + reorder_review_articles(
            [
                content
                for content in content_json
                if content.get("type") not in ["evaluation-summary", "reply"]
            ]
        )
        + [content for content in content_json if content.get("type") == "reply"]
    )
    return content_json


def add_sub_article_xml(
    docmap_string, article_xml, version_doi=None, generate_dois=True
):
    "parse content from docmap and add sub-article tags to the article XML"
    LOGGER.info("Parsing article XML into root Element")
    root = parse.parse_article_xml(article_xml)
    LOGGER.info("Parsing article XML into an Article object")
    article, error_count = parse.article_from_xml(article_xml)
    LOGGER.info("Populate sub article data")
    data = sub_article_data(docmap_string, article, version_doi, generate_dois)
    LOGGER.info("Generate sub-article XML")
    sub_article_xml_root = generate(data)
    LOGGER.info("Appending sub-article tags to the XML root")
    for sub_article_tag in sub_article_xml_root.findall(".//sub-article"):
        root.append(sub_article_tag)
    return root


def sub_article_data(docmap_string, article, version_doi=None, generate_dois=True):
    "parse docmap, get the HTML for each article, and format the content"
    LOGGER.info("Parsing docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    LOGGER.info("Collecting content_json")
    content_json = docmap_parse.docmap_content(d_json, version_doi)
    LOGGER.info("Downloading HTML for each web-content URL")
    content_json = docmap_parse.populate_docmap_content(content_json)
    LOGGER.info("Formatting content json into article and XML data")
    return format_content_json(content_json, article, generate_dois)


def sub_article_id(index):
    "generate an id attribute for a sub article"
    return "sa%s" % index


def sub_article_doi(article_doi, index):
    "generate a DOI for a sub article"
    return "%s.%s" % (article_doi, sub_article_id(index))


EDITOR_REPORT_CONTRIB_TYPES = ["assoc_ed"]


def sub_article_contributors(article_object, sub_article_object, participants=None):
    "add contributors to the sub-article from the parent article depending on the article type"
    if sub_article_object.article_type == "editor-report":
        # add editors of the article as authors of the sub-article
        if article_object.editors:
            for editor in article_object.editors:
                if editor.contrib_type not in EDITOR_REPORT_CONTRIB_TYPES:
                    continue
                author = copy.copy(editor)
                author.contrib_type = "author"
                if not author.roles:
                    author.roles = [Role("Reviewing Editor", "editor")]
                sub_article_object.contributors.append(author)
        elif participants:
            for participant in participants:
                if participant.get("role") == "editor":
                    actor = participant.get("actor")
                    first_name = " ".join(
                        [
                            name_part
                            for name_part in [
                                actor.get("firstName"),
                                actor.get("_middleName"),
                            ]
                            if name_part
                        ]
                    )
                    author = Contributor("author", actor.get("surname"), first_name)
                    author.roles = [Role("Reviewing Editor", "editor")]
                    sub_article_object.contributors.append(author)
    if sub_article_object.article_type == "referee-report":
        # one anonymous author per referee-report
        anonymous_author = Contributor("author", None, None)
        anonymous_author.anonymous = True
        anonymous_author.roles = [Role("Reviewer", "referee")]
        sub_article_object.contributors.append(anonymous_author)
    if sub_article_object.article_type == "author-comment":
        for author in article_object.contributors:
            if not author.roles:
                author.roles = [Role("Author", "author")]
            sub_article_object.contributors.append(author)


def build_sub_article_object(article_object, xml_root, content, index):
    # generate a DOI value and create an article object
    if article_object.version_doi:
        doi_base = article_object.version_doi
    else:
        doi_base = article_object.doi
    sub_article_object = Article(sub_article_doi(doi_base, index))
    # set the article id
    sub_article_object.id = sub_article_id(index)
    # set the article type
    sub_article_object.article_type = ARTICLE_TYPE_MAP.get(
        content.get("type"), content.get("type")
    )
    sub_article_contributors(
        article_object, sub_article_object, content.get("participants")
    )
    # take the article title from the XML
    article_title_tag = xml_root.find(".//front-stub/title-group/article-title")
    if article_title_tag is not None:
        # handle inline tags
        tag_text = ElementTree.tostring(article_title_tag).decode("utf8")
        # remove article-title tag
        sub_article_object.title = tag_text.replace("<article-title>", "").replace(
            "</article-title>", ""
        )
    return sub_article_object


def list_tag_start_value(tag):
    "determine a start value of a list tag"
    try:
        return int(tag.get("start"))
    except TypeError:
        # value is None
        return 1


def copy_list_item_content(from_tag, to_tag, item_prefix):
    "copy the text plus the item_prefix, tail and child tags to the to_tag"

    # copy over the text and add the item_prefix
    tag_text = ""
    if from_tag.text:
        tag_text = from_tag.text
    to_tag.text = "%s. %s" % (item_prefix, tag_text)

    # copy over the tail though it is not expected to have a tail
    to_tag.tail = from_tag.tail

    # copy over any child tags
    for content_tag_index, content_child_tag in enumerate(from_tag.iterfind("*")):
        to_tag.insert(content_tag_index, content_child_tag)


def transform_ordered_lists(content_json):
    "list of list-type order convert each list-item to a p tag"
    for index, content in enumerate(content_json):
        xml_root = ElementTree.fromstring(content.get("xml"))
        for list_tag_parent in xml_root.findall(".//list[@list-type='order']/.."):
            for tag_index, child_tag in enumerate(list_tag_parent.iterfind("*")):
                if child_tag.tag == "list" and child_tag.get("list-type") == "order":
                    start_value = list_tag_start_value(child_tag)
                    for item_index, list_item_tag in enumerate(
                        child_tag.findall("list-item")
                    ):
                        # new p tag to hold the content
                        p_tag = Element("p")

                        list_item_p_tag = list_item_tag.find("p")

                        if list_item_p_tag is not None:
                            content_tag = list_item_p_tag
                        else:
                            # if there is no p tag, take content from the list_item_tag
                            content_tag = list_item_tag

                        copy_list_item_content(
                            content_tag, p_tag, start_value + item_index
                        )

                        # insert the new p tag into the parent tree
                        list_tag_parent.insert(tag_index + item_index, p_tag)

                    # remove the old list tag
                    list_tag_parent.remove(child_tag)

        # replace the xml content
        content_json[index]["xml"] = ElementTree.tostring(xml_root)
    return content_json


def format_content_json(content_json, article_object, generate_dois=True):
    data = []
    # parse html to xml
    content_json = docmap_parse.transform_docmap_content(content_json)
    # only keep items which have html
    content_json = [content for content in content_json if content.get("html")]
    # modify the XML
    content_json = transform_ordered_lists(content_json)
    # reorder the articles
    content_json = reorder_content_json(content_json)
    # create an article for each
    for index, content in enumerate(content_json):

        xml_root = ElementTree.fromstring(content.get("xml"))
        # remove hr tags
        xml_root = utils.remove_tags(xml_root, "hr")

        sub_article_object = build_sub_article_object(
            article_object, xml_root, content, index
        )

        if not generate_dois:
            # reset the DOI to the one from the docmap content
            sub_article_object.doi = content.get("doi")

        data.append(
            {
                "article": sub_article_object,
                "xml_root": xml_root,
            }
        )

    return data


def generate(data, root_tag="article"):
    "generate a sub-article XML tag for each article"
    root = Element(root_tag)

    for data_item in data:
        article = data_item.get("article")
        sub_article_root = data_item.get("xml_root")

        # set the article-type for each article
        sub_article_tag = sub_article(root, article.id, article.article_type)

        # front-stub parent tag
        front_stub_tag = SubElement(sub_article_tag, "front-stub")

        build.set_article_id(front_stub_tag, article)
        build.set_title_group(front_stub_tag, article)

        # add contributor tags
        if article.contributors:
            set_contrib(front_stub_tag, article)

        build.set_related_object(front_stub_tag, article)

        # set body from the sub-article XML
        body_tag = sub_article_root.find("body")
        if body_tag is not None:
            sub_article_tag.append(body_tag)

        # if editor-report, extra formatting for the abstract
        if article.article_type == "editor-report":
            assessment_terms.add_assessment_terms(sub_article_tag)

    # repair namespaces
    repair_namespaces(root)

    return root


def repair_namespaces(root):
    "repair XML namespaces by adding namespaces if missing"
    all_attributes = set()
    for tag in root.iter("*"):
        all_attributes = all_attributes.union(
            all_attributes, {attribute_name for attribute_name in tag.attrib.keys()}
        )
    prefix_attributes = {
        attrib.split(":")[0] for attrib in all_attributes if ":" in attrib
    }

    for prefix in prefix_attributes:
        if prefix in XML_NAMESPACES.keys():
            ns_attrib = "xmlns:%s" % prefix
            root.set(ns_attrib, XML_NAMESPACES.get(prefix))


def sub_article(parent, id_attribute=None, article_type=None):
    sub_article_tag = SubElement(parent, "sub-article")
    if id_attribute:
        sub_article_tag.set("id", id_attribute)
    if article_type:
        sub_article_tag.set("article-type", article_type)
    return sub_article_tag


def set_contrib(parent, article, contrib_type=None):
    contrib_group = SubElement(parent, "contrib-group")

    for contributor in article.contributors:
        contrib_tag = SubElement(contrib_group, "contrib")
        contrib_tag.set("contrib-type", contributor.contrib_type)
        build.set_contrib_name(contrib_tag, contributor)

        # set role tag
        build.set_contrib_role(contrib_tag, contrib_type, contributor)

        # set orcid tag with authenticated=true tag attribute
        build.set_contrib_orcid(contrib_tag, contributor)

        # add aff tag(s)
        for affiliation in contributor.affiliations:
            build.set_aff(
                contrib_tag,
                affiliation,
                contrib_type,
                aff_id=None,
                tail="",
                institution_wrap=True,
            )


def tag_new_line_wrap_text(element):
    "wrap the tag text with a new line character if it has no text"
    if not element.text:
        element.text = "\n"


def tag_new_line_wrap_tail(element):
    "wrap the tag tail with a new line character if it has no tail"
    if not element.tail:
        element.tail = "\n"


def tag_new_line_wrap(element):
    "wrap the tag in a new line character if it has no text or tail"
    tag_new_line_wrap_text(element)
    tag_new_line_wrap_tail(element)


def pretty_sub_article_xml(root):
    "add whitespace to make sub-article output more pretty"
    for sub_article_tag in root.findall(".//sub-article"):
        tag_new_line_wrap(sub_article_tag)
        for tag_name in [
            "aff",
            "article-id",
            "article-title",
            "body",
            "collab",
            "contrib",
            "contrib-group",
            "disp-quote",
            "front-stub",
            "given-names",
            "kwd",
            "kwd-group",
            "name",
            "role",
            "surname",
            "title-group",
        ]:
            for tag in sub_article_tag.findall(".//%s" % tag_name):
                tag_new_line_wrap(tag)
        # wrap tail only for the following tags
        for tag_name in ["anonymous", "etal", "p"]:
            for tag in sub_article_tag.findall(".//%s" % tag_name):
                tag_new_line_wrap_tail(tag)
