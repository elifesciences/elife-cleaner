import os
import re
from collections import OrderedDict
from xml.etree import ElementTree
import html
from wand.image import Image
from wand.exceptions import PolicyError, WandRuntimeError
from elifecleaner import LOGGER, zip_lib


# flag for whether to try and repair XML if it encounters a ParseError
REPAIR_XML = True


def check_ejp_zip(zip_file, tmp_dir):
    "check contents of ejp zip file"
    asset_file_name_map = zip_lib.unzip_zip(zip_file, tmp_dir)
    xml_asset = article_xml_asset(asset_file_name_map)
    root = parse_article_xml(xml_asset[1])
    files = file_list(root)
    figures = figure_list(files, asset_file_name_map)
    zip_file_name = zip_file.split(os.sep)[-1]
    # check for multiple page PDF figures
    for pdf in [pdf for pdf in figures if pdf.get("pages") and pdf.get("pages") > 1]:
        LOGGER.warning(
            "%s multiple page PDF figure file: %s", zip_file_name, pdf.get("file_name")
        )
    # check for missing files
    missing_files = find_missing_files(files, asset_file_name_map)
    for missing_file in missing_files:
        LOGGER.warning(
            "%s does not contain a file in the manifest: %s",
            zip_file_name,
            missing_file,
        )
    # check for file not listed in the manifest
    extra_files = find_extra_files(files, asset_file_name_map)
    for extra_file in extra_files:
        LOGGER.warning(
            "%s has file not listed in the manifest: %s", zip_file_name, extra_file
        )
    # check for out of sequence files by name
    missing_files_by_name = find_missing_files_by_name(files)
    for missing_file in missing_files_by_name:
        LOGGER.warning(
            "%s has file misisng from expected numeric sequence: %s",
            zip_file_name,
            missing_file,
        )

    return True


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
            "match_pattern": r"Figure (\d+)",
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
            # replace (\d) from the match pattern to get a missing file name
            label = label_match.sub(str(expected_number), match_pattern)
            missing_files.append(label)
        prev_number = number

    return missing_files


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
        try:
            return ElementTree.fromstring(xml_string)
        except ElementTree.ParseError:
            if REPAIR_XML:
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
        if figure_detail["extension"] == "pdf":
            figure_detail["pages"] = pdf_page_count(figure_detail.get("file_path"))
        figures.append(figure_detail)
    return figures


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
