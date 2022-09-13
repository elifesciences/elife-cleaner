import os
import zipfile
from collections import OrderedDict


def profile_zip(file_name):
    """open the zip and get relevant file names"""
    zip_asset_infos = []
    with zipfile.ZipFile(file_name, "r") as open_zipfile:
        for zipfile_info in open_zipfile.infolist():
            zip_asset_infos.append(zipfile_info)
    # sort by file name
    zip_asset_infos = sorted(zip_asset_infos, key=lambda asset: asset.filename)
    return zip_asset_infos


def unzip_zip(file_name, temp_dir):
    "unzip certain files and return the local paths"
    asset_file_name_map = OrderedDict()
    zip_asset_infos = profile_zip(file_name)

    # extract the files
    with zipfile.ZipFile(file_name, "r") as open_zipfile:
        for zip_asset_info in zip_asset_infos:
            file_name_parts = zip_asset_info.filename.split("/")
            file_name = file_name_parts[-1]
            folder_name = ""
            if len(file_name_parts) > 1:
                folder_name = file_name_parts[-2]
                folder_path = os.path.join(temp_dir, folder_name)
                if not os.path.exists(folder_path):
                    os.mkdir(folder_path)
            asset_file_name = os.path.join(temp_dir, folder_name, file_name)
            # extract the file
            open_zipfile.extract(zip_asset_info, path=temp_dir)
            # record the file path in the map
            asset_file_name_map[zip_asset_info.filename] = asset_file_name

    return asset_file_name_map
