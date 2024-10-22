import io
import os
import importlib


def delete_files_in_folder(folder, filter_out=None):
    file_list = os.listdir(folder)
    for file_name in file_list:
        file_path = os.path.join(folder, file_name)
        if filter_out and file_name in filter_out:
            continue
        elif os.path.isdir(file_path):
            # call recursively to delete file and folders inside a folder
            delete_files_in_folder(file_path)
            os.rmdir(file_path)
        elif os.path.isfile(file_path):
            os.remove(file_path)


def fixture_module_name(folder_names, filename):
    return ".".join(folder_names + [filename.rstrip(".py")])


def read_fixture(filename, mode="r"):
    folder_names = ["tests", "fixtures"]
    full_filename = os.path.join(os.sep.join(folder_names), filename)
    if full_filename.endswith(".py"):
        # import the fixture and return the value of expected
        module_name = fixture_module_name(folder_names, filename)
        mod = importlib.import_module(module_name)
        # assert expected exists before continuing
        assert hasattr(
            mod, "EXPECTED"
        ), "EXPECTED property not found in module {module_name}".format(
            module_name=module_name
        )
        return mod.EXPECTED
    else:
        kwargs = {"mode": mode}
        if mode == "r":
            kwargs["encoding"] = "utf-8"
        with io.open(full_filename, **kwargs) as file_fp:
            return file_fp.read()


def read_log_file_lines(log_file_path):
    "read log file lines as a list for using in test assertions"
    log_file_lines = []
    with open(log_file_path, "r") as open_file:
        for line in open_file:
            log_file_lines.append(line)
    return log_file_lines


def sub_article_xml_fixture(
    article_type, sub_article_id, front_stub_xml_string, body_xml_string
):
    "generate test fixture XML for a sub-article"
    return (
        b'<sub-article xmlns:xlink="http://www.w3.org/1999/xlink" '
        b'article-type="%s" id="%s">%s%s</sub-article>'
        % (article_type, sub_article_id, front_stub_xml_string, body_xml_string)
    )


class FakeRequest:
    def __init__(self):
        self.headers = {}
        self.body = None


class FakeResponse:
    def __init__(self, status_code, response_json=None, text="", content=None):
        self.status_code = status_code
        self.response_json = response_json
        self.content = content
        self.text = text
        self.request = FakeRequest()
        self.headers = {}

    def json(self):
        return self.response_json
