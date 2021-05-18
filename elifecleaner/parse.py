from elifecleaner import zip_lib


def check_ejp_zip(zip_file, tmp_dir):
    asset_file_name_map = zip_lib.unzip_zip(zip_file, tmp_dir)
    # todo!!!
    return True
