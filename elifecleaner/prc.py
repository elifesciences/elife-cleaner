import time
from xml.etree.ElementTree import Element, SubElement
from docmaptools import parse as docmap_parse
from jatsgenerator import build as jats_build
from elifetools.utils import doi_to_doi_uri
from elifecleaner import LOGGER

# for each ISSN, values for journal-id-type tag text
ISSN_JOURNAL_ID_MAP = {
    "2050-084X": {
        "nlm-ta": "elife",
        "hwp": "eLife",
        "publisher-id": "eLife",
    }
}

# for each ISSN, values for other journal metadata
ISSN_JOURNAL_META_MAP = {
    "2050-084X": {
        "journal-title": "eLife",
        "publisher-name": "eLife Sciences Publications, Ltd",
    }
}


def yield_journal_id_tags(root, journal_id_types):
    "find journal-id tags with matched journal-id-type attribute"
    for journal_id_tag in root.findall("./front/journal-meta/journal-id"):
        if (
            journal_id_tag.get("journal-id-type")
            and journal_id_tag.get("journal-id-type") in journal_id_types
        ):
            yield journal_id_tag


ELOCATION_ID_PRC_TERM = "RP"


def is_xml_prc(root):
    "check if the XML is PRC format by comparing journal-id tag text for a mismatch"
    issn_tag = root.find("./front/journal-meta/issn")
    if issn_tag is not None and issn_tag.text in ISSN_JOURNAL_ID_MAP:
        journal_id_type_map = ISSN_JOURNAL_ID_MAP.get(issn_tag.text)
        # check if any of the journal-id tag values do not match the expected values
        for journal_id_tag in yield_journal_id_tags(root, journal_id_type_map.keys()):
            if journal_id_tag.text != journal_id_type_map.get(
                journal_id_tag.get("journal-id-type")
            ):
                return True
    # also check the elocation-id tag value if the journal meta has already been changed
    elocation_id_tag = root.find(".//front/article-meta/elocation-id")
    if elocation_id_tag is not None:
        if elocation_id_tag.text and elocation_id_tag.text.startswith(
            ELOCATION_ID_PRC_TERM
        ):
            return True
    return False


def transform_journal_id_tags(root, identifier=None):
    "replace file name tags in xml Element with names from file transformations list"
    issn_tag = root.find("./front/journal-meta/issn")
    if issn_tag is not None and issn_tag.text in ISSN_JOURNAL_ID_MAP:
        journal_id_type_map = ISSN_JOURNAL_ID_MAP.get(issn_tag.text)
        for journal_id_tag in yield_journal_id_tags(root, journal_id_type_map.keys()):
            LOGGER.info(
                "%s replacing journal-id tag text of type %s to %s",
                identifier,
                journal_id_tag.get("journal-id-type"),
                journal_id_type_map.get(journal_id_tag.get("journal-id-type")),
            )

            journal_id_tag.text = journal_id_type_map.get(
                journal_id_tag.get("journal-id-type")
            )
    return root


def transform_journal_meta_tag(root, tag_name, tag_path, identifier=None):
    "replace the text value of a tag in the journal meta"
    issn_tag = root.find("./front/journal-meta/issn")
    if issn_tag is not None and issn_tag.text in ISSN_JOURNAL_META_MAP:
        journal_meta_map = ISSN_JOURNAL_META_MAP.get(issn_tag.text)
        journal_title_tag = root.find(tag_path)
        if journal_title_tag is not None and journal_meta_map.get(tag_name):
            LOGGER.info(
                "%s replacing %s tag text to %s",
                identifier,
                tag_name,
                journal_meta_map.get(tag_name),
            )
            journal_title_tag.text = journal_meta_map.get(tag_name)
    return root


def transform_journal_title_tag(root, identifier=None):
    "replace journal-title tag in xml Element with names from file transformations list"
    return transform_journal_meta_tag(
        root,
        "journal-title",
        "./front/journal-meta/journal-title-group/journal-title",
        identifier,
    )


def transform_publisher_name_tag(root, identifier=None):
    "replace publisher-name tag in xml Element with names from file transformations list"
    return transform_journal_meta_tag(
        root,
        "publisher-name",
        "./front/journal-meta/publisher/publisher-name",
        identifier,
    )


def add_prc_custom_meta_tags(root, identifier=None):
    "add custom-meta tag in custom-meta-group"
    article_meta_tag = root.find(".//front/article-meta")
    if article_meta_tag is None:
        LOGGER.warning(
            "%s article-meta tag not found",
            identifier,
        )
        return root
    custom_meta_group_tag = article_meta_tag.find("custom-meta-group")
    if custom_meta_group_tag is None:
        # add the custom-meta-group tag
        custom_meta_group_tag = SubElement(article_meta_tag, "custom-meta-group")
    # add the custom-meta tag
    custom_meta_tag = SubElement(custom_meta_group_tag, "custom-meta")
    custom_meta_tag.set("specific-use", "meta-only")
    meta_name_tag = SubElement(custom_meta_tag, "meta-name")
    meta_name_tag.text = "publishing-route"
    meta_value_tag = SubElement(custom_meta_tag, "meta-value")
    meta_value_tag.text = "prc"
    return root


def elocation_id_from_docmap(docmap_string, version_doi=None, identifier=None):
    "from the docmap get the elocation-id volume"
    LOGGER.info("Parse docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    if not d_json:
        LOGGER.warning(
            "%s parsing docmap returned None",
            identifier,
        )
        return None
    elocation_id = docmap_parse.preprint_electronic_article_identifier(
        d_json, version_doi=version_doi, identifier=identifier
    )
    if not elocation_id:
        LOGGER.warning(
            "%s no elocation_id found in the docmap",
            identifier,
        )
        return None
    return elocation_id


def version_doi_from_docmap(docmap_string, identifier=None, published=True):
    "find the latest preprint DOI from docmap"
    doi = None
    LOGGER.info("Parse docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    if not d_json:
        LOGGER.warning(
            "%s parsing docmap returned None",
            identifier,
        )
        return doi
    LOGGER.info("Get latest preprint data from the docmap")
    preprint_data = docmap_parse.docmap_latest_preprint(d_json, published=published)
    if not preprint_data:
        LOGGER.warning(
            "%s no preprint data was found in the docmap",
            identifier,
        )
        return doi
    LOGGER.info("Find the doi in the docmap preprint data")
    doi = preprint_data.get("doi")
    if not doi:
        LOGGER.warning(
            "%s did not find doi data in the docmap preprint data",
            identifier,
        )
        return doi
    LOGGER.info("Version DOI from the docmap: %s", doi)
    return doi


# maximum supported verison number to check for non-version DOI values
MAX_VERSION = 999


def next_version_doi(doi, identifier=None):
    "generate the next version DOI value"
    if not doi:
        return None
    doi_base, version = doi.rsplit(".", 1)
    # check for integer
    try:
        int(version)
    except ValueError:
        LOGGER.warning(
            "%s version from DOI could not be converted to int, version %s",
            identifier,
            version,
        )
        return None
    if int(version) > MAX_VERSION:
        LOGGER.warning(
            "%s failed to determine the version from DOI, version %s exceeds MAX_VERSION %s",
            identifier,
            version,
            MAX_VERSION,
        )
        return None
    next_version = int(version) + 1
    next_doi = "%s.%s" % (doi_base, next_version)
    LOGGER.info(
        "%s next version doi, from DOI %s, next DOI %s", identifier, doi, next_doi
    )
    return next_doi


def add_article_id(parent, text, pub_id_type, specific_use=None):
    "add article-id tag"
    # add article-id tag
    article_id_tag = Element("article-id")
    article_id_tag.set("pub-id-type", pub_id_type)
    if specific_use:
        article_id_tag.set("specific-use", specific_use)
    article_id_tag.text = text
    # insert the new tag into the XML after the last article-id tag
    insert_index = 1
    for tag_index, tag in enumerate(parent.findall("*")):
        if tag.tag == "article-id":
            insert_index = tag_index + 1
    parent.insert(insert_index, article_id_tag)


def add_doi(root, doi, specific_use=None, identifier=None):
    "add article-id tag for the doi to article-meta tag"
    article_meta_tag = root.find(".//front/article-meta")
    if article_meta_tag is None:
        LOGGER.warning(
            "%s article-meta tag not found",
            identifier,
        )
        return root
    # add version DOI article-id tag
    add_article_id(article_meta_tag, doi, pub_id_type="doi", specific_use=specific_use)
    return root


def add_version_doi(root, doi, identifier=None):
    "add version article-id tag for the doi to article-meta tag"
    return add_doi(root, doi, specific_use="version", identifier=identifier)


def review_date_from_docmap(docmap_string, identifier=None):
    "find the under-review date for the first preprint from the docmap"
    date_string = None
    LOGGER.info("Parse docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    if not d_json:
        LOGGER.warning(
            "%s parsing docmap returned None",
            identifier,
        )
        return date_string
    LOGGER.info("Get first under-review happened date from the docmap")
    date_string = docmap_parse.preprint_review_date(d_json)
    if not date_string:
        LOGGER.warning(
            "%s no under-review happened date was found in the docmap",
            identifier,
        )
    return date_string


def volume_from_docmap(docmap_string, version_doi=None, identifier=None):
    "from the docmap get the volume"
    LOGGER.info("Parse docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    if not d_json:
        LOGGER.warning(
            "%s parsing docmap returned None",
            identifier,
        )
        return None
    volume = docmap_parse.preprint_volume(
        d_json, version_doi=version_doi, identifier=identifier
    )
    if volume:
        try:
            volume = int(volume)
        except ValueError:
            LOGGER.warning(
                "%s volume from the docmap could not be cast as int",
                identifier,
            )
            return None
    else:
        LOGGER.warning(
            "%s no volume found in the docmap",
            identifier,
        )
        return None
    return volume


def license_from_docmap(docmap_string, version_doi=None, identifier=None):
    "from the docmap get the license"
    LOGGER.info("Parse docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    if not d_json:
        LOGGER.warning(
            "%s parsing docmap returned None",
            identifier,
        )
        return None
    license_url = docmap_parse.preprint_license(
        d_json, version_doi=version_doi, identifier=identifier
    )
    if not license_url:
        LOGGER.warning(
            "%s no license found in the docmap",
            identifier,
        )
        return None
    return license_url


def article_categories_from_docmap(docmap_string, version_doi=None, identifier=None):
    "from the docmap get the article category subject disciplines"
    LOGGER.info("Parse docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    if not d_json:
        LOGGER.warning(
            "%s parsing docmap returned None",
            identifier,
        )
        return None
    article_categories = docmap_parse.preprint_subject_disciplines(
        d_json, version_doi=version_doi, identifier=identifier
    )
    if not article_categories:
        LOGGER.warning(
            "%s no article_categories found in the docmap",
            identifier,
        )
        return None
    return article_categories


def date_struct_from_string(date_string):
    "parse the date_string into time.struct_time"
    formats = ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]
    for date_format in formats:
        try:
            return time.strptime(date_string, date_format)
        except ValueError:
            LOGGER.info(
                'unable to parse "%s" using format "%s"',
                date_string,
                date_format,
            )
    return None


def add_history_date(root, date_type, date_struct, identifier=None):
    "find or add the history tag and add a date to it"
    article_meta_tag = root.find(".//front/article-meta")
    if article_meta_tag is None:
        LOGGER.warning(
            "%s article-meta tag not found",
            identifier,
        )
        return root
    # look for an existing history tag
    history_tag = article_meta_tag.find("./history")
    # if no history tag, add one
    if history_tag is None:
        # insert the new tag into the XML after the elocation-id tag
        insert_index = 1
        for tag_index, tag in enumerate(article_meta_tag.findall("*")):
            if tag.tag == "elocation-id":
                insert_index = tag_index + 1
        history_tag = Element("history")
        article_meta_tag.insert(insert_index, history_tag)
    # add date tag to the history tag
    date_tag = SubElement(history_tag, "date")
    if date_type:
        date_tag.set("date-type", date_type)
    jats_build.set_dmy(date_tag, date_struct)
    return root


EVENT_DESC_PREPRINT = "This manuscript was published as a preprint."
EVENT_DESC_REVIEWED_PREPRINT = "This manuscript was published as a reviewed preprint."
EVENT_DESC_REVISED_PREPRINT = "The reviewed preprint was revised."


def add_pub_history(root, history_data, identifier=None):
    "add the pub-history tag and add event data to it"
    if not history_data:
        return root
    article_meta_tag = root.find(".//front/article-meta")
    if article_meta_tag is None:
        LOGGER.warning(
            "%s article-meta tag not found",
            identifier,
        )
        return root
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
    # add event tags to the pub-history tag
    added_reviewed_preprint = None
    for history_event_data in history_data:
        event_tag = SubElement(pub_history_tag, "event")
        if history_event_data.get("type"):
            if history_event_data.get("type") == "preprint":
                event_desc_tag = SubElement(event_tag, "event-desc")
                event_desc_tag.text = EVENT_DESC_PREPRINT
            elif history_event_data.get("type") == "reviewed-preprint":
                event_desc_tag = SubElement(event_tag, "event-desc")
                if added_reviewed_preprint:
                    # already added one reviewed-preprint
                    event_desc_tag.text = EVENT_DESC_REVISED_PREPRINT
                else:
                    # adding the first reviewed-preprint
                    event_desc_tag.text = EVENT_DESC_REVIEWED_PREPRINT
                added_reviewed_preprint = True
        if history_event_data.get("date"):
            date_struct = date_struct_from_string(history_event_data.get("date"))
            date_tag = SubElement(event_tag, "date")
            if history_event_data.get("type"):
                date_tag.set("date-type", history_event_data.get("type"))
            jats_build.set_dmy(date_tag, date_struct)
            date_tag.set("iso-8601-date", time.strftime("%Y-%m-%d", date_struct))
            if history_event_data.get("doi"):
                self_uri_tag = SubElement(event_tag, "self-uri")
                if history_event_data.get("type"):
                    self_uri_tag.set("content-type", history_event_data.get("type"))
                self_uri_tag.set(
                    "{http://www.w3.org/1999/xlink}href",
                    doi_to_doi_uri(history_event_data.get("doi")),
                )
    return root
