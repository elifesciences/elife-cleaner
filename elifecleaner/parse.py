import re
from collections import OrderedDict
from xml.etree import ElementTree
import html
from wand.image import Image
from wand.exceptions import PolicyError, WandRuntimeError
from elifecleaner import LOGGER, zip_lib


def check_ejp_zip(zip_file, tmp_dir):
    "check contents of ejp zip file"
    asset_file_name_map = zip_lib.unzip_zip(zip_file, tmp_dir)
    xml_asset = article_xml_asset(asset_file_name_map)
    root = parse_article_xml(xml_asset[1])
    files = file_list(root)
    figures = figure_list(files, asset_file_name_map)
    # check for multiple page PDF figures
    for pdf in [pdf for pdf in figures if pdf.get("pages") and pdf.get("pages") > 1]:
        LOGGER.warning("multiple page PDF figure file: %s", pdf.get("file_name"))
    return True


def article_xml_asset(asset_file_name_map):
    """
    find the article XML file name,
    e.g. 30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml
    """
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
            # try to repair the xml namespaces
            xml_string = repair_article_xml(xml_string)
            return ElementTree.fromstring(xml_string)


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
        return re.sub(
            r"<article(.*?)>",
            r'<article\1 xmlns:xlink="http://www.w3.org/1999/xlink">',
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
