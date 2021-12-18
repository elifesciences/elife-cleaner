import copy
import os
import zipfile
from elifetools import xmlio
from elifetools import parseJATS as parser
from elifecleaner import LOGGER, parse, zip_lib


class ArticleZipFile:
    "data structure for holding details about files in a zip with a manifest XML"

    def __init__(self, xml_name=None, zip_name=None, file_path=None):
        self.xml_name = xml_name
        self.zip_name = zip_name
        self.file_path = file_path

    def __repr__(self):
        return 'ArticleZipFile("%s", "%s", "%s")' % (
            self.xml_name,
            self.zip_name,
            self.file_path,
        )


def transform_ejp_zip(zip_file, tmp_dir, output_dir):
    "transform ejp zip file and write a new zip file output"

    new_zip_file_path = None
    zip_file_name = zip_file.split(os.sep)[-1]

    # start logging
    LOGGER.info("%s starting to transform", zip_file_name)

    # profile the zip contents
    asset_file_name_map = zip_lib.unzip_zip(zip_file, tmp_dir)
    xml_asset = parse.article_xml_asset(asset_file_name_map)
    xml_asset_path = xml_asset[1]
    root = parse.parse_article_xml(xml_asset_path)

    code_files = code_file_list(root)

    # zip code files
    file_transformations = []
    for file_data in code_files:
        code_file_name = file_data.get("upload_file_nm")

        LOGGER.info("%s code_file_name: %s" % (zip_file_name, code_file_name))
        # collect file name data
        original_code_file_name, original_code_file_path = find_in_file_name_map(
            code_file_name, asset_file_name_map
        )

        from_file = ArticleZipFile(
            code_file_name, original_code_file_name, original_code_file_path
        )
        LOGGER.info("%s from_file: %s" % (zip_file_name, from_file))

        to_file = zip_code_file(from_file, output_dir)
        LOGGER.info("%s to_file: %s" % (zip_file_name, to_file))

        # save the from file to file transformation
        file_transformations.append((from_file, to_file))

    # rewrite the XML tags
    LOGGER.info("%s rewriting xml tags" % zip_file_name)
    root = transform_xml_file_tags(root, file_transformations)

    # remove history tags from XML for certain article types
    soup = parser.parse_document(xml_asset_path)
    root = transform_xml_history_tags(root, soup, zip_file_name)

    # write new XML file
    xml_string = xml_element_to_string(root)
    LOGGER.info("%s writing xml to file %s" % (zip_file_name, xml_asset_path))
    with open(xml_asset_path, "w") as open_file:
        open_file.write(xml_string)

    # create a new asset map
    new_asset_file_name_map = transform_asset_file_name_map(
        asset_file_name_map, file_transformations
    )

    # write new zip file
    new_zip_file_path = os.path.join(output_dir, zip_file_name)
    LOGGER.info("%s writing new zip file %s" % (zip_file_name, new_zip_file_path))
    create_zip_from_file_map(new_zip_file_path, new_asset_file_name_map)

    return new_zip_file_path


def xml_element_to_string(root):
    xmlio.register_xmlns()
    return xmlio.output_root(root, None, None)


def code_file_list(root):
    code_files = []

    files = parse.file_list(root)

    aux_files = [
        file_data for file_data in files if file_data.get("file_type") == "aux_file"
    ]

    for file_data in aux_files:
        if file_data.get("upload_file_nm").endswith(".zip"):
            # if it is already a zip file, skip it
            continue
        code_files.append(file_data)

    return code_files


def find_in_file_name_map(file_name, file_name_map):
    for asset_file_name, file_name_path in file_name_map.items():
        if file_name_path.endswith(file_name):
            return asset_file_name, file_name_path
    return None, None


def zip_code_file(from_file, output_dir):
    "zip a code file and put new zip details into an ArticleZipFile struct"
    code_file_zip_name = from_file.zip_name + ".zip"
    new_code_file_name = from_file.xml_name + ".zip"
    code_file_zip_path = os.path.join(output_dir, new_code_file_name)

    to_file = ArticleZipFile(new_code_file_name, code_file_zip_name, code_file_zip_path)

    with zipfile.ZipFile(code_file_zip_path, "w") as open_zipfile:
        open_zipfile.write(from_file.file_path, from_file.zip_name)

    return to_file


def from_file_to_file_map(file_transformations):
    "convert a list of file transformations into a dict keyed on their xml file name"
    return {
        from_file.xml_name: to_file.xml_name
        for from_file, to_file in file_transformations
    }


def transform_xml_file_tags(root, file_transformations):
    "replace file name tags in xml Element with names from file transformations list"
    xml_file_name_transforms = from_file_to_file_map(file_transformations)
    for file_nm_tag in root.findall("./front/article-meta/files/file/upload_file_nm"):
        if file_nm_tag.text in xml_file_name_transforms:
            file_nm_tag.text = xml_file_name_transforms.get(file_nm_tag.text)
    return root


def transform_xml_history_tags(root, soup, zip_file_name):
    "remove history tags from the XML for particular article types"
    article_type = parser.article_type(soup)
    display_channel_list = parser.display_channel(soup)
    LOGGER.info(
        "%s article_type %s, display_channel %s"
        % (zip_file_name, article_type, display_channel_list)
    )
    if article_type in ["correction", "editorial", "retraction"] or (
        article_type == "article-commentary"
        and "insight" in [value.lower() for value in display_channel_list if value]
    ):
        LOGGER.info("%s transforming xml history tags" % zip_file_name)
        # remove history tag
        for history_tag in root.findall("./front/article-meta/history"):
            root.find("./front/article-meta").remove(history_tag)
    return root


def transform_asset_file_name_map(asset_file_name_map, file_transformations):
    "replace file name details in the map with those from the list of file transformations"
    new_asset_file_name_map = copy.copy(asset_file_name_map)
    for from_file, to_file in file_transformations:
        if from_file.zip_name in new_asset_file_name_map:
            del new_asset_file_name_map[from_file.zip_name]
            new_asset_file_name_map[to_file.zip_name] = to_file.file_path
    return new_asset_file_name_map


def create_zip_from_file_map(zip_path, file_name_map):
    "write the files to a zip"
    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as open_zip:
        for file_name, file_path in file_name_map.items():
            open_zip.write(file_path, file_name)
