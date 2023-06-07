import time
from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from elifearticle.article import ArticleDate
from elifecleaner import parse
from elifecleaner.utils import NAMESPACE_MAP, pad_msid

JOURNAL_ID_TYPES = ["nlm-ta", "publisher-id"]

MEDIA_CONTENT_TYPE = "glencoe play-in-place height-250 width-310"

DTD_VERSION = "1.1d1"


def set_pub_date(parent, article, pub_type):
    "set XML pub-date tag to values from an article date"
    pub_date = article.get_date(pub_type)
    if pub_date:
        date_tag = SubElement(parent, "pub-date")
        date_tag.set("date-type", pub_type)
        if pub_date.publication_format:
            date_tag.set("publication-format", pub_date.publication_format)
        day = SubElement(date_tag, "day")
        day.text = str(pub_date.date.tm_mday).zfill(2)
        month = SubElement(date_tag, "month")
        month.text = str(pub_date.date.tm_mon).zfill(2)
        year = SubElement(date_tag, "year")
        year.text = str(pub_date.date.tm_year)


def set_article_meta(parent, article):
    "set XML article-meta tag and tags found inside it"
    article_meta = SubElement(parent, "article-meta")

    # article-id pub-id-type="publisher-id"
    if article.manuscript:
        pub_id_type = "publisher-id"
        article_id = SubElement(article_meta, "article-id")
        article_id.text = pad_msid(article.manuscript)
        article_id.set("pub-id-type", pub_id_type)

    # article-id pub-id-type="doi"
    if article.doi:
        pub_id_type = "doi"
        article_id = SubElement(article_meta, "article-id")
        article_id.text = article.doi
        article_id.set("pub-id-type", pub_id_type)

    set_pub_date(article_meta, article, "publication")


def set_front(parent, journal_data, article):
    "set XML front tag and the tags found inside it"
    front_tag = SubElement(parent, "front")
    journal_meta = SubElement(front_tag, "journal-meta")

    # journal-id
    if journal_data.get("journal_ids"):
        for journal_id_type, value in journal_data.get("journal_ids").items():
            # concatenate the config name to look for the value
            if journal_id_type:
                journal_id = SubElement(journal_meta, "journal-id")
                journal_id.set("journal-id-type", journal_id_type)
                journal_id.text = value
    # journal-title-group
    journal_title_group = SubElement(journal_meta, "journal-title-group")

    # journal-title
    if journal_data.get("journal_title"):
        journal_title_tag = SubElement(journal_title_group, "journal-title")
        journal_title_tag.text = journal_data.get("journal_title")

    # publisher
    if journal_data.get("publisher_name"):
        publisher = SubElement(journal_meta, "publisher")
        publisher_name_tag = SubElement(publisher, "publisher-name")
        publisher_name_tag.text = journal_data.get("publisher_name")

    set_article_meta(front_tag, article)


def set_body(parent, video_data):
    "set XML body tag contents"
    body_tag = SubElement(parent, "body")
    # video media tags
    for video in video_data:
        media_tag = SubElement(body_tag, "media")
        media_tag.set("xlink:href", video.get("video_filename"))
        media_tag.set("id", video.get("video_id"))
        media_tag.set("content-type", MEDIA_CONTENT_TYPE)
        media_tag.set("mimetype", "video")


def output_xml(root, pretty=False, indent=""):
    "output root XML Element to a string"
    encoding = "utf-8"
    rough_string = ElementTree.tostring(root, encoding)
    reparsed = minidom.parseString(rough_string)

    if pretty is True:
        return reparsed.toprettyxml(indent, encoding=encoding)
    return reparsed.toxml(encoding=encoding)


def generate_xml(article, journal_data, video_data, pretty=True, indent=""):
    "from jats_content generate final JATS output"

    # set the date to today
    article_date = ArticleDate("publication", time.gmtime())
    article_date.publication_format = "electronic"
    article.add_date(article_date)

    # Create the root XML node
    root = Element("article")
    # set attributes
    root.set("dtd-version", DTD_VERSION)
    root.set("article-type", article.article_type)
    # set namespaces
    for prefix, url in NAMESPACE_MAP.items():
        root.set(prefix, url)

    set_front(root, journal_data, article)
    set_body(root, video_data)

    return output_xml(root, pretty, indent)


def glencoe_xml(xml_file_path, video_data, pretty=True, indent=""):
    "generate XML to be submitted to Glencoe"
    # build an Article object from the XML
    article, error_count = parse.article_from_xml(xml_file_path)
    # collect journal data from the XML elementtree
    root = parse.parse_article_xml(xml_file_path)
    journal_ids = parse.xml_journal_id_values(root)
    filtered_journal_ids = {
        key: value for key, value in journal_ids.items() if key in JOURNAL_ID_TYPES
    }
    journal_title = parse.xml_journal_title(root)
    publisher_name = parse.xml_publisher_name(root)
    journal_data = {
        "journal_ids": filtered_journal_ids,
        "journal_title": journal_title,
        "publisher_name": publisher_name,
    }
    return generate_xml(article, journal_data, video_data, pretty, indent)
