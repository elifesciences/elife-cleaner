import time
from xml.etree.ElementTree import Element, SubElement
from docmaptools import parse as docmap_parse
from jatsgenerator import build as jats_build
from elifetools.utils import doi_to_doi_uri
from elifecleaner import sub_article, LOGGER
from elifecleaner.prc import date_struct_from_string


def prune_history_data(history_data, doi, version):
    "return history data related to doi for versions less than version provided"
    return [
        data
        for data in history_data
        if not data.get("doi").startswith(doi)
        or (
            data.get("doi").startswith(doi)
            and data.get("versionIdentifier")
            and int(data.get("versionIdentifier")) < int(version)
        )
    ]


def find_pub_history_tag(root, identifier=None):
    "find pub-history tag in the article-meta tag"
    article_meta_tag = root.find(".//front/article-meta")
    if article_meta_tag is None:
        LOGGER.warning(
            "%s article-meta tag not found",
            identifier,
        )
        return None
    # look for an existing pub-history tag
    pub_history_tag = article_meta_tag.find("./pub-history")
    # if no pub-history tag, add one
    if pub_history_tag is None:
        # insert the new tag into the XML after the history or elocation-id tag
        insert_index = 1
        for tag_index, tag in enumerate(article_meta_tag.findall("*")):
            if tag.tag in "history":
                insert_index = tag_index + 1
                break
            if tag.tag == "elocation-id":
                insert_index = tag_index + 1
        pub_history_tag = Element("pub-history")
        article_meta_tag.insert(insert_index, pub_history_tag)
    return pub_history_tag


def add_self_uri_tag(parent, article_type, uri, title):
    "add self-uri tag for each peer review in event tag"
    self_uri_tag = SubElement(parent, "self-uri")
    if article_type:
        self_uri_tag.set("content-type", article_type)
    self_uri_tag.set(
        "{http://www.w3.org/1999/xlink}href",
        uri,
    )
    self_uri_tag.text = str(title)


def add_history_event_tag(parent, event_data):
    "add event tag to pub-history"
    event_tag = SubElement(parent, "event")
    if event_data.get("event_desc"):
        event_desc_tag = SubElement(event_tag, "event-desc")
        event_desc_tag.text = event_data.get("event_desc")
    if event_data.get("date"):
        date_struct = date_struct_from_string(event_data.get("date"))
        date_tag = SubElement(event_tag, "date")
        if event_data.get("type"):
            date_tag.set("date-type", event_data.get("type"))
        jats_build.set_dmy(date_tag, date_struct)
        date_tag.set("iso-8601-date", time.strftime("%Y-%m-%d", date_struct))
        if event_data.get("doi"):
            self_uri_tag = SubElement(event_tag, "self-uri")
            if event_data.get("type"):
                self_uri_tag.set("content-type", event_data.get("type"))
            self_uri_tag.set(
                "{http://www.w3.org/1999/xlink}href",
                doi_to_doi_uri(event_data.get("doi")),
            )
    if event_data.get("self_uri_list"):
        for self_uri_data in event_data.get("self_uri_list"):
            add_self_uri_tag(
                event_tag,
                self_uri_data.get("content_type"),
                self_uri_data.get("uri"),
                self_uri_data.get("title"),
            )


EVENT_DESC_PREPRINT = "This manuscript was published as a preprint."
EVENT_DESC_REVIEWED_PREPRINT = "This manuscript was published as a reviewed preprint."
EVENT_DESC_REVISED_PREPRINT = "The reviewed preprint was revised."

MECA_EVENT_DESC_PREPRINT = "Preprint posted"
MECA_EVENT_DESC_REVIEWED_PREPRINT = "Reviewed preprint"
MECA_EVENT_DESC_REVISED_PREPRINT = "Reviewed preprint"


def preprint_event_desc(style):
    "generate event event-desc tag text for a preprint history event"
    event_description = None
    if style == "accepted":
        event_description = EVENT_DESC_PREPRINT
    elif style == "meca":
        event_description = MECA_EVENT_DESC_PREPRINT
    return event_description


def reviewed_preprint_event_desc(style, first_review_event, version):
    "generate event event-desc tag text for a reviewed preprint history event"
    event_description = None
    extra = ""
    if style == "meca" and version:
        extra = " v%s" % version
    if first_review_event:
        # adding the first reviewed-preprint
        if style == "accepted":
            event_description = "%s%s" % (
                EVENT_DESC_REVIEWED_PREPRINT,
                extra,
            )
        elif style == "meca":
            event_description = "%s%s" % (
                MECA_EVENT_DESC_REVIEWED_PREPRINT,
                extra,
            )
    else:
        # already added one reviewed-preprint
        if style == "accepted":
            event_description = "%s%s" % (
                EVENT_DESC_REVISED_PREPRINT,
                extra,
            )
        elif style == "meca":
            event_description = "%s%s" % (
                MECA_EVENT_DESC_REVISED_PREPRINT,
                extra,
            )
    return event_description


def history_event_self_uri_list(docmap_string, version_doi):
    "a list of self-uri tag data for a history event"
    self_uri_list = []
    d_json = docmap_parse.docmap_json(docmap_string)
    step_map = docmap_parse.preprint_version_doi_step_map(d_json)
    if step_map.get(version_doi):
        generate_dois = False
        data = sub_article.sub_article_data(
            docmap_string,
            version_doi=version_doi,
            generate_dois=generate_dois,
        )
        for data_item in data:
            self_uri_data = {}
            if data_item.get("article").article_type:
                self_uri_data["content_type"] = data_item.get("article").article_type
            self_uri_data["uri"] = doi_to_doi_uri(data_item.get("article").doi)
            self_uri_data["title"] = str(data_item.get("article").title)
            self_uri_list.append(self_uri_data)
    return self_uri_list


def collect_history_event_data(
    history_data, style, docmap_string=None, add_self_uri=False
):
    "populate a list of history event data"
    history_event_data = []
    if not history_data:
        return history_event_data
    first_review_event = True
    for data in history_data:
        event_data = {}
        event_data["type"] = data.get("type")
        event_data["date"] = data.get("date")
        event_data["doi"] = data.get("doi")
        event_data["versionIdentifier"] = data.get("versionIdentifier")
        # event description
        if event_data.get("type") == "preprint":
            event_data["event_desc"] = preprint_event_desc(style)
        elif event_data.get("type") == "reviewed-preprint":
            event_data["event_desc"] = reviewed_preprint_event_desc(
                style, first_review_event, event_data.get("versionIdentifier")
            )
            first_review_event = False
        # self-uri values
        if add_self_uri and docmap_string:
            event_data["self_uri_list"] = history_event_self_uri_list(
                docmap_string, version_doi=event_data.get("doi")
            )
        # append the event data to the list
        history_event_data.append(event_data)
    return history_event_data


def add_pub_history_tag(root, history_event_data, identifier=None):
    "set event data in pub-history tag"
    if not history_event_data:
        return root
    pub_history_tag = find_pub_history_tag(root, identifier)
    if pub_history_tag is None:
        return root
    # add event tags to the pub-history tag
    for event_data in history_event_data:
        add_history_event_tag(
            pub_history_tag,
            event_data,
        )
    return root


def add_pub_history(root, history_data, docmap_string=None, identifier=None):
    "add the pub-history tag and add event data to it"
    style = "accepted"
    add_self_uri = False
    # collect history event data
    history_event_data = collect_history_event_data(
        history_data, style, docmap_string, add_self_uri
    )
    return add_pub_history_tag(root, history_event_data, identifier)


def add_pub_history_meca(root, history_data, docmap_string=None, identifier=None):
    "add the MECA style pub-history tag and add event data to it"
    style = "meca"
    add_self_uri = True
    # collect history event data
    history_event_data = collect_history_event_data(
        history_data, style, docmap_string, add_self_uri
    )
    return add_pub_history_tag(root, history_event_data, identifier)
