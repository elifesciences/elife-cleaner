import os
import re
from collections import OrderedDict
from xml.etree import ElementTree
import html
from wand.image import Image
from wand.exceptions import PolicyError, WandRuntimeError
from elifearticle import parse as articleparse
from elifetools.utils import escape_ampersand
from elifecleaner import LOGGER, pdf_utils, utils, zip_lib


# flag for whether to try and repair XML if it encounters a ParseError
REPAIR_XML = True

# acceptable file extensions for an art_file
ART_FILE_EXTENSIONS = ["doc", "docx", "tex"]


def article_from_xml(xml_file_path):
    "parse using elifearticle library into an Article object"
    return articleparse.build_article_from_xml(xml_file_path)


def check_ejp_zip(zip_file, tmp_dir):
    "check contents of ejp zip file"
    asset_file_name_map = zip_lib.unzip_zip(zip_file, tmp_dir)
    xml_asset = article_xml_asset(asset_file_name_map)
    root = parse_article_xml(xml_asset[1])
    files = file_list(root)
    # use the zip file name as the identifier for log messages
    identifer = zip_file.split(os.sep)[-1]
    return check_files(files, asset_file_name_map, identifer)


def check_files(files, asset_file_name_map, identifier):
    figures = figure_list(files, asset_file_name_map)
    figures = set_figure_pdf_pages_count(figures)
    # check for multiple page PDF figures
    check_multi_page_figure_pdf(figures, identifier)
    # check for missing files
    check_missing_files(files, asset_file_name_map, identifier)
    # check for file not listed in the manifest
    extra_files = check_extra_files(files, asset_file_name_map, identifier)
    # check for out of sequence files by name
    check_missing_files_by_name(files, identifier)
    # check the art file type
    check_art_file(files, identifier)
    return True


def check_multi_page_figure_pdf(figures, identifier):
    pdfimages_available = pdf_utils.pdfimages_exists()
    for pdf in [pdf for pdf in figures if pdf.get("pages") and pdf.get("pages") > 1]:
        is_multi_page = False
        if pdfimages_available:
            LOGGER.info(
                "%s using pdfimages to check PDF figure file: %s",
                identifier,
                pdf.get("file_name"),
            )
            try:
                image_pages = pdf_utils.pdf_image_pages(pdf.get("file_path"))
                LOGGER.info(
                    "%s pdfimages found images on pages %s in PDF figure file: %s",
                    identifier,
                    image_pages,
                    pdf.get("file_name"),
                )
                is_multi_page = bool([page for page in image_pages if page > 1])
            except:
                LOGGER.exception(
                    "%s exception using pdfimages to check PDF figure file: %s",
                    identifier,
                    pdf.get("file_name"),
                )
                # consider it multi page in the case pdfimages raises an exception
                is_multi_page = True
        else:
            is_multi_page = True
        if is_multi_page:
            LOGGER.warning(
                "%s multiple page PDF figure file: %s",
                identifier,
                pdf.get("file_name"),
            )


def check_missing_files(files, asset_file_name_map, identifier):
    "check for missing files and log a warning if missing"
    missing_files = find_missing_files(files, asset_file_name_map)
    for missing_file in missing_files:
        LOGGER.warning(
            "%s does not contain a file in the manifest: %s",
            identifier,
            missing_file,
        )


def find_missing_files(files, asset_file_name_map):
    "for each file name from the manifest XML file, check for missing files in the zip contents"
    missing_files = []
    asset_file_name_keys = [
        asset_file_key.split("/")[-1] for asset_file_key in asset_file_name_map
    ]
    for manifest_file in files:
        if manifest_file.get("upload_file_nm") not in asset_file_name_keys:
            missing_files.append(manifest_file.get("upload_file_nm"))
    return missing_files


def check_extra_files(files, asset_file_name_map, identifier):
    "check for extra files and log them as a warning if present"
    extra_files = find_extra_files(files, asset_file_name_map)
    for extra_file in extra_files:
        LOGGER.warning(
            "%s has file not listed in the manifest: %s", identifier, extra_file
        )


def find_extra_files(files, asset_file_name_map):
    "check if any file names are missing from the manifest XML"
    extra_files = []

    asset_file_name_keys = [
        asset_file_key.split("/")[-1] for asset_file_key in asset_file_name_map
    ]
    manifest_file_names = [
        manifest_file.get("upload_file_nm")
        for manifest_file in files
        if manifest_file.get("upload_file_nm")
    ]

    # get the name of the article XML file for later
    xml_asset_file_name = None
    xml_asset = article_xml_asset(asset_file_name_map)
    if xml_asset:
        xml_asset_file_name = xml_asset[0].split("/")[-1]

    for file_name in asset_file_name_keys:
        # skip checking for the XML file which is not listed in the manifest
        if file_name == xml_asset_file_name:
            continue
        if file_name not in manifest_file_names:
            extra_files.append(file_name)
    return extra_files


def check_missing_files_by_name(files, identifier):
    "check for files numbered out of sequence and log a warning when found"
    missing_files_by_name = find_missing_files_by_name(files)
    for missing_file in missing_files_by_name:
        LOGGER.warning(
            "%s has file missing from expected numeric sequence: %s",
            identifier,
            missing_file,
        )


def find_missing_files_by_name(files):
    """
    In the manifest file names look for any missing from the expected numeric sequence
    For example, if there is only Figure 1 and Figure 3, Figure 2 is consider to be missing
    """
    missing_files = []
    match_rules = [
        {
            "file_types": ["figure"],
            "meta_names": ["Title", "Figure number"],
            "match_pattern": r"Figure\s+(\d+)",
        }
    ]
    for match_rule in match_rules:

        # collect file values
        file_detail_values = find_file_detail_values(
            files,
            match_rule.get("file_types"),
            match_rule.get("meta_names"),
        )
        meta_values = [file_detail[1] for file_detail in file_detail_values]

        missing_files += find_missing_value_by_sequence(
            meta_values, match_rule.get("match_pattern")
        )
    return missing_files


def find_file_detail_values(files, file_types, meta_names):
    file_detail_values = []
    file_types = list(file_types)
    for file_data in files:
        if file_data.get("file_type") in file_types and file_data.get("custom_meta"):
            for custom_meta in file_data.get("custom_meta"):
                if (
                    custom_meta.get("meta_name")
                    and custom_meta.get("meta_name") in meta_names
                ):
                    # create a tuple of file_type and number
                    file_details = (
                        file_data.get("file_type"),
                        custom_meta.get("meta_value"),
                    )
                    file_detail_values.append(file_details)
                    # only take the first match
                    break
    return file_detail_values


def find_missing_value_by_sequence(values, match_pattern):
    """
    from list of values, use match pattern to collect a numeric sequence and check for
    numbers missing from the sequence
    For example, match_pattern of r"Figure (\\d+)" to get a list of 1, 2, 3, n
    (note: two backslashes are used for one backslash in the above example
     to avoid DeprecationWarning: invalid escape sequence in this comment)
    """
    missing_files = []

    figure_meta_value_match = re.compile(match_pattern)
    label_match = re.compile(r"\(\\d.?\)")

    number_list = []
    for meta_value in values:
        match = figure_meta_value_match.match(meta_value)
        if match:
            number_list.append(int(match.group(1)))

    number_list.sort()

    prev_number = None
    for number in number_list:
        expected_number = None
        if prev_number:
            expected_number = prev_number + 1
        if expected_number and number > expected_number:
            # remove whitespace match pattern
            label_pattern = match_pattern.replace(r"\s+", " ")
            # replace (\d) from the match pattern to get a missing file name
            label = label_match.sub(str(expected_number), label_pattern)
            missing_files.append(label)
        prev_number = number

    return missing_files


def check_art_file(files, identifier):
    "check for an art file and it is an acceptable type"
    art_files = [
        file_data for file_data in files if file_data.get("file_type") == "art_file"
    ]
    file_extensions = [
        utils.file_extension(file_data.get("upload_file_nm"))
        for file_data in art_files
        if file_data.get("upload_file_nm")
    ]
    # convert values to lowercase when comparing
    good_file_extensions = [
        extension
        for extension in file_extensions
        if extension.lower() in ART_FILE_EXTENSIONS
    ]
    if not art_files or not good_file_extensions:
        LOGGER.warning(
            "%s could not find a word or latex article file in the package",
            identifier,
        )


def article_xml_asset(asset_file_name_map):
    """
    find the article XML file name,
    e.g. 30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml
    """
    if not asset_file_name_map:
        return None
    xml_asset = None
    match_pattern = re.compile(r"^(.*)/\1.xml$")
    for asset in asset_file_name_map.items():
        if re.match(match_pattern, asset[0]):
            xml_asset = asset
            break
    return xml_asset


def parse_article_xml(xml_file):
    with open(xml_file, "r") as open_file:
        xml_string = open_file.read()
        # unescape any HTML entities to avoid undefined entity XML exceptions later
        xml_string = html_entity_unescape(xml_string)
        # fix XML-incompatible character entities
        if utils.match_control_character_entities(xml_string):
            LOGGER.info(
                "Replacing character entities in the XML string: %s"
                % utils.match_control_character_entities(xml_string)
            )
            xml_string = utils.replace_control_character_entities(xml_string)
        # also replace unescaped control characters
        if utils.match_control_characters(xml_string):
            LOGGER.info(
                "Replacing control characters in the XML string (ASCII codes): %s"
                % [ord(char) for char in utils.match_control_characters(xml_string)]
            )
            xml_string = utils.replace_control_characters(xml_string)
        try:
            return ElementTree.fromstring(xml_string)
        except ElementTree.ParseError:
            if REPAIR_XML:
                # fix ampersands
                xml_string = escape_ampersand(xml_string)
                # try to repair the xml namespaces
                xml_string = repair_article_xml(xml_string)
                return ElementTree.fromstring(xml_string)
            else:
                LOGGER.exception("ParseError raised because REPAIR_XML flag is False")
                raise


def replace_entity(match):
    "function to use in re.sub for HTMTL entity replacements"
    entity_name = match.group(1)
    ignore_entities = [
        "amp",
        "lt",
        "gt",
    ]
    if entity_name in html.entities.entitydefs and entity_name not in ignore_entities:
        return html.entities.entitydefs[entity_name]
    else:
        return "&%s;" % entity_name


def html_entity_unescape(xml_string):
    "convert HTML entities to unicode characters, except the XML special characters"
    if "&" not in xml_string:
        return xml_string
    match_pattern = re.compile(r"&([^\t\n\f <&#;]{1,32}?);")
    return match_pattern.sub(replace_entity, xml_string)


def repair_article_xml(xml_string):
    if 'xmlns:xlink="http://www.w3.org/1999/xlink"' not in xml_string:
        article_match_pattern = re.compile(r"<article>|<article(\s{1,}.*?)>")
        replacement_pattern = r'<article\1 xmlns:xlink="http://www.w3.org/1999/xlink">'
        return article_match_pattern.sub(
            replacement_pattern,
            xml_string,
        )
    return xml_string


def xml_journal_id_values(root):
    "parse journal-id tags from the XML ElementTree"
    values = {}
    for journal_id_tag in root.findall("./front/journal-meta/journal-id"):
        if journal_id_tag.attrib.get("journal-id-type"):
            values[journal_id_tag.attrib.get("journal-id-type")] = journal_id_tag.text
    return values


def xml_journal_title(root):
    "parse the journal title from the XML ElementTree"
    title = None
    for journal_title_tag in root.findall(
        "./front/journal-meta/journal-title-group/journal-title"
    ):
        title = journal_title_tag.text
        break
    return title


def xml_publisher_name(root):
    "parse the publisher name from the XML ElementTree"
    name = None
    for publisher_name_tag in root.findall(
        "./front/journal-meta/publisher/publisher-name"
    ):
        name = publisher_name_tag.text
        break
    return name


def file_list(root):
    file_list = []
    attribute_map = {
        "file-type": "file_type",
        "id": "id",
    }
    tag_name_map = {
        "upload_file_nm": "upload_file_nm",
    }
    custom_meta_tag_name_map = {
        "meta-name": "meta_name",
        "meta-value": "meta_value",
    }
    for file_tag in root.findall("./front/article-meta/files/file"):
        file_detail = OrderedDict()
        for from_key, to_key in attribute_map.items():
            file_detail[to_key] = file_tag.attrib.get(from_key)
        for from_key, to_key in tag_name_map.items():
            tag = file_tag.find(from_key)
            if tag is not None:
                file_detail[to_key] = tag.text
        custom_meta_tags = tag = file_tag.findall("custom-meta")
        if custom_meta_tags is not None:
            file_detail["custom_meta"] = []
            custom_meta = OrderedDict()
            for custom_meta_tag in custom_meta_tags:
                custom_meta = OrderedDict()
                for from_key, to_key in custom_meta_tag_name_map.items():
                    tag = custom_meta_tag.find(from_key)
                    if tag is not None:
                        custom_meta[to_key] = tag.text
                file_detail["custom_meta"].append(custom_meta)
        file_list.append(file_detail)
    return file_list


def figure_list(files, asset_file_name_map):
    "identify which files are a figure and collect some data about them"
    figures = []

    figure_files = [
        file_data for file_data in files if file_data.get("file_type") == "figure"
    ]

    for file_data in figure_files:
        figure_detail = OrderedDict()
        figure_detail["upload_file_nm"] = file_data.get("upload_file_nm")
        figure_detail["extension"] = file_extension(file_data.get("upload_file_nm"))
        # collect file name data
        for asset_file_name in asset_file_name_map.items():
            if asset_file_name[1].endswith(file_data.get("upload_file_nm")):
                figure_detail["file_name"] = asset_file_name[0]
                figure_detail["file_path"] = asset_file_name[1]
                break
        figures.append(figure_detail)
    return figures


def set_figure_pdf_pages_count(figure_assets):
    "for the pdf files count the number of pages and set the property"
    for figure_detail in figure_assets:
        if figure_detail["extension"] == "pdf":
            figure_detail["pages"] = pdf_page_count(figure_detail.get("file_path"))
    return figure_assets


def file_extension(file_name):
    return file_name.split(".")[-1].lower() if file_name and "." in file_name else None


def pdf_page_count(file_path):
    "open PDF as an image and count the number of pages"
    if file_path:
        try:
            with Image(filename=file_path) as img:
                return len(img.sequence)
        except WandRuntimeError:
            LOGGER.exception(
                "WandRuntimeError in pdf_page_count(), "
                "imagemagick may not be installed"
            )
            raise
        except PolicyError:
            LOGGER.exception(
                "PolicyError in pdf_page_count(), "
                "imagemagick policy.xml may not allow reading PDF files"
            )
            raise
    return None


def preprint_url(root):
    "parse XML to find a preprint URL"
    url = None
    for fn_group_tag in root.findall(
        './front/article-meta/fn-group[@content-type="article-history"]'
    ):
        ext_link_tag = fn_group_tag.find('./ext-link[@ext-link-type="url"]')
        if ext_link_tag is not None:
            url = ext_link_tag.get("{http://www.w3.org/1999/xlink}href")
    return url
