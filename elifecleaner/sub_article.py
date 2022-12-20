import copy
import re
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from elifearticle.article import Article, Contributor, Role
from docmaptools import parse as docmap_parse
from jatsgenerator import build
from elifecleaner import LOGGER, parse

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
        print(content.get("xml"))
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


def add_sub_article_xml(docmap_string, article_xml):
    "parse content from docmap and add sub-article tags to the article XML"
    LOGGER.info("Parsing article XML into root Element")
    root = parse.parse_article_xml(article_xml)
    LOGGER.info("Parsing article XML into an Article object")
    article, error_count = parse.article_from_xml(article_xml)
    LOGGER.info("Populate sub article data")
    data = sub_article_data(docmap_string, article)
    LOGGER.info("Generate sub-article XML")
    sub_article_xml_root = generate(data)
    LOGGER.info("Appending sub-article tags to the XML root")
    for sub_article_tag in sub_article_xml_root.findall(".//sub-article"):
        root.append(sub_article_tag)
    return root


def sub_article_data(docmap_string, article):
    "parse docmap, get the HTML for each article, and format the content"
    LOGGER.info("Parsing docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    LOGGER.info("Collecting content_json")
    content_json = docmap_parse.docmap_content(d_json)
    LOGGER.info("Downloading HTML for each web-content URL")
    content_json = docmap_parse.populate_docmap_content(content_json)
    LOGGER.info("Formatting content json into article and XML data")
    return format_content_json(content_json, article)


def sub_article_id(index):
    "generate an id attribute for a sub article"
    return "sa%s" % index


def sub_article_doi(article_doi, index):
    "generate a DOI for a sub article"
    return "%s.%s" % (article_doi, sub_article_id(index))


def sub_article_contributors(article_object, sub_article_object):
    "add contributors to the sub-article from the parent article depending on the article type"
    if sub_article_object.article_type == "editor-report":
        # add editors of the article as authors of the sub-article
        for editor in article_object.editors:
            author = copy.copy(editor)
            author.contrib_type = "author"
            if not author.roles:
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
    sub_article_object = Article(sub_article_doi(article_object.doi, index))
    # set the article id
    sub_article_object.id = sub_article_id(index)
    # set the article type
    sub_article_object.article_type = ARTICLE_TYPE_MAP.get(
        content.get("type"), content.get("type")
    )
    sub_article_contributors(article_object, sub_article_object)
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


def format_content_json(content_json, article_object):
    data = []
    # parse html to xml
    content_json = docmap_parse.transform_docmap_content(content_json)
    # reorder the articles
    content_json = reorder_content_json(content_json)
    # create an article for each
    for index, content in enumerate(content_json):

        xml_root = ElementTree.fromstring(content.get("xml"))
        sub_article_object = build_sub_article_object(
            article_object, xml_root, content, index
        )

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
