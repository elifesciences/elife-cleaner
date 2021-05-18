import os


def delete_files_in_folder(folder, filter_out=[]):
    file_list = os.listdir(folder)
    for file_name in file_list:
        file_path = os.path.join(folder, file_name)
        if file_name in filter_out:
            continue
        elif os.path.isdir(file_path):
            # call recursively to delete file and folders inside a folder
            delete_files_in_folder(file_path)
            os.rmdir(file_path)
        elif os.path.isfile(file_path):
            os.remove(file_path)
