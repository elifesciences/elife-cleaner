import time
from xml.etree.ElementTree import Element, SubElement
from docmaptools import parse as docmap_parse
from elifearticle.article import Affiliation, Contributor, Role
from elifetools import xmlio
from jatsgenerator import build as jats_build
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


def article_id_from_docmap(docmap_string, version_doi=None, identifier=None):
    "from the docmap get the article_id"
    LOGGER.info("Parse docmap json")
    d_json = docmap_parse.docmap_json(docmap_string)
    if not d_json:
        LOGGER.warning(
            "%s parsing docmap returned None",
            identifier,
        )
        return None
    article_id = docmap_parse.preprint_identifier(
        d_json, version_doi=version_doi, identifier=identifier
    )
    if not article_id:
        LOGGER.warning(
            "%s no article_id found in the docmap",
            identifier,
        )
        return None
    return article_id


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
        date_tag.set("iso-8601-date", time.strftime("%Y-%m-%d", date_struct))
    jats_build.set_dmy(date_tag, date_struct)
    return root


def set_article_id(xml_root, article_id, doi, version_doi):
    "add article-id tags"
    # add manuscript ID
    if article_id:
        article_meta_tag = xml_root.find(".//front/article-meta")
        article_id_tag = Element("article-id")
        article_id_tag.set("pub-id-type", "publisher-id")
        article_id_tag.text = str(article_id)
        article_meta_tag.insert(0, article_id_tag)
    # add regular DOI tag
    add_doi(xml_root, doi, specific_use=None, identifier=version_doi)
    # add version DOI tag
    add_version_doi(xml_root, version_doi, version_doi)


def set_volume(root, volume):
    "set volume tag text, add volume tag if not present"
    # find volume tag
    tag = root.find(".//front/article-meta/volume")
    if tag is None:
        article_meta_tag = root.find(".//front/article-meta")
        if article_meta_tag is not None:
            # add volume tag
            tag_index = xmlio.get_first_element_index(article_meta_tag, "elocation-id")
            if tag_index:
                # insert volume tag in the right tag order
                tag = Element("volume")
                article_meta_tag.insert(tag_index - 1, tag)
            else:
                # append to the end of article-meta
                tag = SubElement(article_meta_tag, "volume")
    if tag is not None:
        tag.text = str(volume)


def set_elocation_id(root, elocation_id):
    "set elocation-id tag text, add elocation-id tag if not present"
    # find elocation-id tag
    tag = root.find(".//front/article-meta/elocation-id")
    if tag is None:
        article_meta_tag = root.find(".//front/article-meta")
        if article_meta_tag is not None:
            # add elocation-id tag
            tag_index = xmlio.get_first_element_index(article_meta_tag, "volume")
            if tag_index:
                # insert elocation-id tag in the right tag order
                tag = Element("elocation-id")
                article_meta_tag.insert(tag_index, tag)
            else:
                # append to the end of article-meta
                tag = SubElement(article_meta_tag, "elocation-id")
    if tag is not None:
        tag.text = str(elocation_id)


def set_article_categories(xml_root, display_channel=None, article_categories=None):
    "add tags to article-categories tag"
    article_meta_tag = xml_root.find(".//front/article-meta")
    article_categories_tag = article_meta_tag.find(".//article-categories")
    if article_categories_tag is None:
        # insert the new tag into the XML after the article-id tags and before title-group
        insert_index = None
        for tag_index, tag in enumerate(article_meta_tag.findall("*")):
            if tag.tag == "article-id":
                insert_index = tag_index + 1
            if tag.tag == "title-group":
                break
        article_categories_tag = Element("article-categories")
        article_meta_tag.insert(insert_index, article_categories_tag)

    if article_categories_tag is not None and display_channel:
        jats_build.set_display_channel(article_categories_tag, display_channel)

    if article_categories_tag is not None and article_categories:
        for article_category in article_categories:
            jats_build.set_major_subject_area(article_categories_tag, article_category)


def set_license_tag(parent, license_data_dict):
    "add license tag to parent tag"
    if not license_data_dict.get("href"):
        return
    license_tag = SubElement(parent, "license")
    license_tag.set(
        "{http://www.w3.org/1999/xlink}href",
        str(license_data_dict.get("href")),
    )
    ali_license_href_tag = SubElement(
        license_tag, "{http://www.niso.org/schemas/ali/1.0/}license_ref"
    )
    ali_license_href_tag.text = license_data_dict.get("href")
    # license-p tag
    license_p_tag = SubElement(license_tag, "license-p")
    license_p_tag.text = license_data_dict.get("paragraph1")
    license_ext_link_tag = SubElement(license_p_tag, "ext-link")
    license_ext_link_tag.set("ext-link-type", "uri")
    license_ext_link_tag.set(
        "{http://www.w3.org/1999/xlink}href",
        license_data_dict.get("href"),
    )
    license_ext_link_tag.text = license_data_dict.get("name")
    license_ext_link_tag.tail = license_data_dict.get("paragraph2")


def set_permissions(xml_root, license_data_dict, copyright_year, copyright_holder):
    "add license data to permissions tag"
    article_meta_tag = xml_root.find(".//front/article-meta")
    permissions_tag = article_meta_tag.find("./permissions")
    if permissions_tag is None:
        # insert the new tag into the XML after the pub-history or history tag
        insert_index = None
        for tag_index, tag in enumerate(article_meta_tag.findall("*")):
            if tag.tag == "pub-history":
                insert_index = tag_index + 1
                break
            if tag.tag == "history":
                insert_index = tag_index + 1
        permissions_tag = Element("permissions")
        article_meta_tag.insert(insert_index, permissions_tag)
    if license_data_dict:
        if license_data_dict.get("copyright"):
            jats_build.set_copyright_tags(
                permissions_tag, copyright_year, copyright_holder
            )
        ali_free_to_read_tag = SubElement(
            permissions_tag, "{http://www.niso.org/schemas/ali/1.0/}free_to_read"
        )
        set_license_tag(permissions_tag, license_data_dict)


CONTRIB_TYPE_ROLE_MAP = {"editor": "Reviewing Editor", "senior_editor": "Senior Editor"}


def editor_contributors(docmap_string, version_doi):
    "populate Contributor objects with editor data from a docmap"
    editors = []

    data = docmap_parse.docmap_editor_data(docmap_string, version_doi)

    for data_item in data:
        contrib_type = data_item.get("role", "").replace("-", "_")
        roles = []
        aff = None
        if contrib_type:
            editor_role = Role()
            editor_role.text = CONTRIB_TYPE_ROLE_MAP.get(contrib_type)
            roles.append(editor_role)
        if data_item.get("actor"):
            surname = data_item.get("actor").get("surname")
            given_name = " ".join(
                [
                    name_part
                    for name_part in [
                        data_item.get("actor").get("firstName"),
                        data_item.get("actor").get("_middleName"),
                    ]
                    if name_part
                ]
            )
            # format affiliation
            affiliation_data_dict = data_item.get("actor").get("affiliation")
            if affiliation_data_dict:
                aff = Affiliation()
                if (
                    affiliation_data_dict.get("name")
                    and affiliation_data_dict.get("type") == "organization"
                ):
                    aff.institution = (
                        data_item.get("actor").get("affiliation").get("name")
                    )
                if affiliation_data_dict.get("location"):
                    # parse and set city and country values
                    location_parts = affiliation_data_dict.get("location").split(",")
                    if len(location_parts) == 2:
                        aff.city = location_parts[0]
                        aff.country = location_parts[1].lstrip()

        editor = Contributor(contrib_type, surname, given_name)
        editor.roles = roles
        if aff:
            editor.set_affiliation(aff)
        editors.append(editor)

    return editors


def set_editors(parent, editors):
    "set editor contrib tags"
    if not editors:
        return
    # find where to insert a contrib-group tag
    insert_index = None
    for tag_index, tag in enumerate(parent.findall("*")):
        if tag.tag == "contrib-group":
            insert_index = tag_index + 1
    # insert contrib-group tag
    contrib_group_tag = Element("contrib-group")
    if insert_index:
        parent.insert(insert_index, contrib_group_tag)
    else:
        parent.append(contrib_group_tag)
    contrib_group_tag.set("content-type", "section")
    for editor in editors:
        contrib_tag = SubElement(contrib_group_tag, "contrib")
        contrib_tag.set("contrib-type", editor.contrib_type)
        jats_build.set_contrib_name(contrib_tag, editor)
        jats_build.set_contrib_orcid(contrib_tag, editor)
        # role tag
        jats_build.set_contrib_role(contrib_tag, editor.contrib_type, editor)
        # add inline aff tags
        for affiliation in editor.affiliations:
            jats_build.set_aff(
                contrib_tag,
                affiliation,
                editor.contrib_type,
                tail="",
                institution_wrap=True,
            )
