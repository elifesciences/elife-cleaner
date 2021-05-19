import re
from elifecleaner import zip_lib


def check_ejp_zip(zip_file, tmp_dir):
    asset_file_name_map = zip_lib.unzip_zip(zip_file, tmp_dir)
    # todo!!!
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
