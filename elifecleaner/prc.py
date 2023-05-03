import re
from xml.etree.ElementTree import Element, SubElement
from docmaptools import parse as docmap_parse
from elifecleaner import LOGGER

# for each ISSN, values for journal-id-type tag text
ISSN_JOURNAL_ID_MAP = {
    "2050-084X": {
        "nlm-ta": "elife",
        "hwp": "eLife",
        "publisher-id": "eLife",
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


def is_xml_prc(root):
    "check if the XML is PRC format by comparing journal-id tag text for a mismatch"
    issn_tag = root.find("./front/journal-meta/issn")
    if issn_tag is None:
        return False
    if issn_tag.text in ISSN_JOURNAL_ID_MAP:
        journal_id_type_map = ISSN_JOURNAL_ID_MAP.get(issn_tag.text)
        # check if any of the journal-id tag values do not match the expected values
        for journal_id_tag in yield_journal_id_tags(root, journal_id_type_map.keys()):
            if journal_id_tag.text != journal_id_type_map.get(
                journal_id_tag.get("journal-id-type")
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


ELOCATION_ID_MATCH_PATTERN = r"e(.*)"

ELOCATION_ID_REPLACEMENT_PATTERN = r"RP\1"


def transform_elocation_id(
    root,
    from_pattern=ELOCATION_ID_MATCH_PATTERN,
    to_pattern=ELOCATION_ID_REPLACEMENT_PATTERN,
    identifier=None,
):
    "change the elocation-id tag text value"
    elocation_id_tag = root.find(".//front/article-meta/elocation-id")
    if elocation_id_tag is not None:
        match_pattern = re.compile(from_pattern)
        new_elocation_id = match_pattern.sub(
            to_pattern,
            elocation_id_tag.text,
        )
        if new_elocation_id != elocation_id_tag.text:
            LOGGER.info(
                "%s changing elocation-id value %s to %s",
                identifier,
                elocation_id_tag.text,
                new_elocation_id,
            )
            elocation_id_tag.text = new_elocation_id
    return root


def version_doi_from_docmap(docmap_string, identifier=None):
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
    preprint_data = docmap_parse.docmap_latest_preprint(d_json)
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


def add_version_doi(root, doi, identifier=None):
    "add version article-id tag for the doi to article-meta tag"
    article_meta_tag = root.find(".//front/article-meta")
    if article_meta_tag is None:
        LOGGER.warning(
            "%s article-meta tag not found",
            identifier,
        )
        return root
    # add article-id tag
    article_id_tag = Element("article-id")
    article_id_tag.set("pub-id-type", "doi")
    article_id_tag.set("specific-use", "version")
    article_id_tag.text = doi
    # insert the new tag into the XML after the last article-id tag
    insert_index = 1
    for tag_index, tag in enumerate(article_meta_tag.findall("*")):
        if tag.tag == "article-id":
            insert_index = tag_index + 1
    article_meta_tag.insert(insert_index, article_id_tag)
    return root
