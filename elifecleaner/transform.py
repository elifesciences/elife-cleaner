import copy
from xml.etree.ElementTree import SubElement
import os
import string
import zipfile
from elifetools import xmlio
from elifetools import parseJATS as parser
from elifecleaner import LOGGER, parse, prc, zip_lib


WELLCOME_FUNDING_STATEMENT = "For the purpose of Open Access, the authors have applied a CC BY public copyright license to any Author Accepted Manuscript version arising from this submission."


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

    zip_file_name = zip_file.split(os.sep)[-1]

    # profile the zip contents
    asset_file_name_map = zip_lib.unzip_zip(zip_file, tmp_dir)

    # start logging
    LOGGER.info("%s starting to transform", zip_file_name)

    new_asset_file_name_map = transform_ejp_files(
        asset_file_name_map, output_dir, zip_file_name
    )

    # write new zip file
    new_zip_file_path = rezip(new_asset_file_name_map, output_dir, zip_file_name)

    return new_zip_file_path


def transform_ejp_files(asset_file_name_map, output_dir, identifier):
    "transform ejp files and XML"
    xml_asset = parse.article_xml_asset(asset_file_name_map)
    xml_asset_path = xml_asset[1]

    new_asset_file_name_map = transform_code_files(
        asset_file_name_map, output_dir, identifier
    )

    transform_xml(xml_asset_path, identifier)
    return new_asset_file_name_map


def transform_code_files(asset_file_name_map, output_dir, identifier):
    "zip code files if they are not already a zip file"
    # parse XML file
    xml_asset = parse.article_xml_asset(asset_file_name_map)
    xml_asset_path = xml_asset[1]
    root = parse.parse_article_xml(xml_asset_path)

    file_transformations = code_file_transformations(
        root, asset_file_name_map, output_dir, identifier
    )
    code_file_zip(file_transformations, output_dir, identifier)

    # create a new asset map
    new_asset_file_name_map = transform_asset_file_name_map(
        asset_file_name_map, file_transformations
    )

    xml_rewrite_file_tags(xml_asset_path, file_transformations, identifier)
    return new_asset_file_name_map


def code_file_transformations(root, asset_file_name_map, output_dir, identifier):
    # zip code files
    code_files = code_file_list(root)
    file_transformations = []
    for file_data in code_files:
        code_file_name = file_data.get("upload_file_nm")

        LOGGER.info("%s code_file_name: %s", identifier, code_file_name)
        # collect file name data
        original_code_file_name, original_code_file_path = find_in_file_name_map(
            code_file_name, asset_file_name_map
        )

        from_file = ArticleZipFile(
            code_file_name, original_code_file_name, original_code_file_path
        )
        LOGGER.info("%s from_file: %s", identifier, from_file)

        to_file = zip_code_file(from_file, output_dir)
        LOGGER.info("%s to_file: %s", identifier, to_file)

        # save the from file to file transformation
        file_transformations.append((from_file, to_file))
    return file_transformations


def code_file_zip(file_transformations, output_dir, identifier):
    for from_file, to_file in file_transformations:
        LOGGER.info(
            "%s zipping from_file: %s, to_file: %s", identifier, from_file, to_file
        )
        to_file = zip_code_file(from_file, output_dir)


def cover_art_file_list(root):
    'get a list of cover_art from the XML with @file-type="cover_art"'
    files = parse.file_list(root)
    return [
        file_data for file_data in files if file_data.get("file_type") == "cover_art"
    ]


def transform_cover_art_files(
    xml_file_path, asset_file_name_map, file_transformations, identifier
):
    "rename cover art files"
    # create a new asset map
    new_asset_file_name_map = transform_asset_file_name_map(
        asset_file_name_map, file_transformations
    )

    xml_rewrite_file_tags(xml_file_path, file_transformations, identifier)
    return new_asset_file_name_map


STRIKING_IMAGE_FILE_NAME_PATTERN = "{article_id}-{index}_striking_image.{extension}"


def striking_image_file_name(file_name, article_id, index):
    "generate a new name for the striking image"
    # alpha character from the index 0 to 25, supports up to 26 characters
    alpha_index = list(string.ascii_lowercase)[index]
    extension = file_name.rsplit(".", 1)[-1]
    return STRIKING_IMAGE_FILE_NAME_PATTERN.format(
        article_id=article_id, index=alpha_index, extension=extension
    )


def cover_art_file_transformations(
    cover_art_files, asset_file_name_map, article_id, identifier
):
    file_transformations = []
    for index, cover_art_file in enumerate(cover_art_files):
        # list of old file names
        previous_href = cover_art_file.get("upload_file_nm")

        LOGGER.info("%s cover_art file name: %s", identifier, previous_href)
        # collect file name data
        original_file_name, original_file_path = find_in_file_name_map(
            previous_href, asset_file_name_map
        )

        from_file = ArticleZipFile(
            previous_href, original_file_name, original_file_path
        )
        LOGGER.info("%s from_file: %s", identifier, from_file)
        # generate a new file name
        current_href = striking_image_file_name(previous_href, article_id, index)
        new_file_name = original_file_name.rsplit("/", 1)[0] + "/" + current_href
        new_file_path = original_file_path.rsplit("/", 1)[0] + "/" + current_href
        to_file = ArticleZipFile(current_href, new_file_name, new_file_path)
        LOGGER.info("%s to_file: %s", identifier, to_file)

        # save the from file to file transformation
        file_transformations.append((from_file, to_file))
    return file_transformations


def xml_rewrite_file_tags(xml_asset_path, file_transformations, identifier):
    root = parse.parse_article_xml(xml_asset_path)
    # rewrite the XML tags
    LOGGER.info("%s rewriting xml tags", identifier)
    root = transform_xml_file_tags(root, file_transformations)
    write_xml_file(root, xml_asset_path, identifier)


def transform_xml(xml_asset_path, identifier):
    "modify the XML"
    # remove history tags from XML for certain article types
    root = parse.parse_article_xml(xml_asset_path)
    soup = parser.parse_document(xml_asset_path)
    root = transform_subject_tags(root, identifier)
    root = transform_kwd_tags(root, identifier)
    root = transform_xml_history_tags(root, soup, identifier)
    root = transform_xml_funding(root, identifier)
    write_xml_file(root, xml_asset_path, identifier)


def write_xml_file(
    root,
    xml_asset_path,
    identifier,
    doctype_dict=None,
    encoding=None,
    processing_instructions=None,
):
    # write new XML file
    doctype = None
    if doctype_dict is not None:
        publicId = doctype_dict.get("pubid")
        systemId = doctype_dict.get("system")
        qualifiedName = doctype_dict.get("name")
        doctype = xmlio.build_doctype(qualifiedName, publicId, systemId)
    xml_string = xml_element_to_string(
        root,
        doctype=doctype,
        encoding=encoding,
        processing_instructions=processing_instructions,
    )
    LOGGER.info("%s writing xml to file %s", identifier, xml_asset_path)
    with open(xml_asset_path, "w") as open_file:
        open_file.write(xml_string)


def xml_element_to_string(
    root, doctype=None, encoding=None, processing_instructions=None
):
    xmlio.register_xmlns()
    return xmlio.output_root(
        root,
        doctype=doctype,
        encoding=None,
        processing_instructions=processing_instructions,
    )


def code_file_list(root):
    "get a list of code files from the file tags in the ElementTree"
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
    "find the item in the map matching the file_name"
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


def transform_subject_tags(root, identifier):
    "modify values and remove duplicate subject tags"
    # remove unwanted portion of subject value
    for subject_tag in root.findall("./front/article-meta/article-categories//subject"):
        subject_tag.text = subject_tag.text.replace("(VOR)", "").rstrip()
    # remove duplicate subject tags
    subject_set = set()
    article_categories_tag = root.find("front/article-meta/article-categories")
    for subject_group_tag in article_categories_tag.findall("subj-group"):
        subject_tag = subject_group_tag.find("subject")
        if subject_tag is not None:
            if subject_tag.text in subject_set:
                LOGGER.info(
                    "%s removing duplicate subject tag %s"
                    % (identifier, subject_tag.text)
                )
                article_categories_tag.remove(subject_group_tag)
            subject_set.add(subject_tag.text)
    return root


def transform_kwd_tags(root, identifier):
    "remove duplicate kwd tags"
    # for each kwd-group tag, look for and remove duplicate kwd tags
    for kwd_group_tag in root.findall("front/article-meta/kwd-group"):
        kwd_set = set()
        for kwd_tag in kwd_group_tag.findall("kwd"):
            if kwd_tag.text in kwd_set:
                LOGGER.info(
                    "%s removing duplicate kwd tag %s" % (identifier, kwd_tag.text)
                )
                kwd_group_tag.remove(kwd_tag)
            kwd_set.add(kwd_tag.text)
    return root


def transform_xml_file_tags(root, file_transformations):
    "replace file name tags in xml Element with names from file transformations list"
    xml_file_name_transforms = from_file_to_file_map(file_transformations)
    for file_nm_tag in root.findall("./front/article-meta/files/file/upload_file_nm"):
        if file_nm_tag.text in xml_file_name_transforms:
            file_nm_tag.text = xml_file_name_transforms.get(file_nm_tag.text)
    return root


# when transforming history tag keep date tags having a date-type in the list below
KEEP_HISTORY_DATE_TYPES = ["sent-for-review"]


def transform_xml_history_tags(root, soup, zip_file_name):
    "remove history tags from the XML for particular article types"
    article_type = parser.article_type(soup)
    display_channel_list = parser.display_channel(soup)
    LOGGER.info(
        "%s article_type %s, display_channel %s",
        zip_file_name,
        article_type,
        display_channel_list,
    )

    if (
        article_type in ["correction", "editorial", "retraction"]
        or (
            article_type == "article-commentary"
            and "insight" in [value.lower() for value in display_channel_list if value]
        )
        or prc.is_xml_prc(root)
    ):
        LOGGER.info("%s transforming xml history tags", zip_file_name)
        # remove date tags from the history tag
        for history_tag in root.findall("./front/article-meta/history"):
            for date_tag in history_tag.findall("./date"):
                if date_tag.get("date-type") not in KEEP_HISTORY_DATE_TYPES:
                    history_tag.remove(date_tag)
        # remove the history tag if it is empty
        for history_tag in root.findall("./front/article-meta/history"):
            if len(history_tag.findall("*")) <= 0:
                root.find("./front/article-meta").remove(history_tag)
    return root


def transform_xml_funding(root, zip_file_name):
    "alter the content in the XML <funding-group> tags"
    # get funder names
    funding_sources = []
    for funding_source_tag in root.findall(
        ".//front/article-meta/funding-group/award-group/funding-source"
    ):
        funding_sources.append(funding_source_tag.text)
    LOGGER.info(
        "%s funding_sources %s",
        zip_file_name,
        funding_sources,
    )
    # look for Wellcome term
    wellcome = bool(
        [funding for funding in funding_sources if "wellcome" in funding.lower()]
    )

    add_funding_statement = False
    funding_statement_tag = None
    funding_statement = None

    if wellcome is True:
        # if Wellcome then look for funding-statement sentence
        LOGGER.info(
            "%s wellcome term found in funding_sources",
            zip_file_name,
        )

        funding_statement_tag = root.find(
            ".//front/article-meta/funding-group/award-group/funding-statement"
        )

        if funding_statement_tag:
            # use the text from the first tag found only
            funding_statement = funding_statement_tag.text
        if WELLCOME_FUNDING_STATEMENT not in str(funding_statement):
            add_funding_statement = True

    # if the sentence is not in funding-statement, then add to the funding statement
    if add_funding_statement:
        if not funding_statement_tag:
            # if no funding-statement tag is present, add it
            LOGGER.info(
                "%s adding a funding-statement tag to the first award-group tag",
                zip_file_name,
            )
            first_award_group_tag = root.find(
                ".//front/article-meta/funding-group/award-group"
            )
            if first_award_group_tag:
                funding_statement_tag = SubElement(
                    first_award_group_tag, "funding-statement"
                )

        # modify the funding-statement tag text
        LOGGER.info(
            "%s adding the WELLCOME_FUNDING_STATEMENT to the funding-statement",
            zip_file_name,
        )
        funding_statement_tag.text = ". ".join(
            [
                part
                for part in [funding_statement_tag.text, WELLCOME_FUNDING_STATEMENT]
                if part
            ]
        )

    return root


def transform_asset_file_name_map(asset_file_name_map, file_transformations):
    "replace file name details in the map with those from the list of file transformations"
    new_asset_file_name_map = copy.copy(asset_file_name_map)
    for from_file, to_file in file_transformations:
        if from_file.zip_name in new_asset_file_name_map:
            del new_asset_file_name_map[from_file.zip_name]
            new_asset_file_name_map[to_file.zip_name] = to_file.file_path
    return new_asset_file_name_map


def rezip(asset_file_name_map, output_dir, zip_file_name):
    "write new zip file"
    new_zip_file_path = os.path.join(output_dir, zip_file_name)
    LOGGER.info("%s writing new zip file %s", zip_file_name, new_zip_file_path)
    create_zip_from_file_map(new_zip_file_path, asset_file_name_map)
    return new_zip_file_path


def create_zip_from_file_map(zip_path, file_name_map):
    "write the files to a zip"
    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as open_zip:
        for file_name, file_path in file_name_map.items():
            open_zip.write(file_path, file_name)
