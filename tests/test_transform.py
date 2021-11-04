import io
import os
import unittest
import zipfile
from xml.etree import ElementTree
from elifecleaner import LOGGER, configure_logging, transform
from elifecleaner.transform import ArticleZipFile
from tests.helpers import delete_files_in_folder, read_fixture


class TestArticleZipFile(unittest.TestCase):
    def test_instantiate(self):
        xml_name = "sub_folder/file.txt"
        zip_name = "file.txt"
        file_path = "local_folder/sub_folder/file.txt"
        from_file = ArticleZipFile(xml_name, zip_name, file_path)
        expected = 'ArticleZipFile("%s", "%s", "%s")' % (xml_name, zip_name, file_path)
        self.assertEqual(str(from_file), expected)


class TestTransform(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.output_dir = "tests/tmp_output"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])
        delete_files_in_folder(self.output_dir, filter_out=[".keepme"])

    def test_transform_ejp_zip(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        zip_file_name = zip_file.split(os.sep)[-1]
        info_prefix = (
            "INFO elifecleaner:transform:transform_ejp_zip: %s"
        ) % zip_file_name
        expected_new_zip_file_path = os.path.join(self.output_dir, zip_file_name)
        new_zip_file_path = transform.transform_ejp_zip(
            zip_file, self.temp_dir, self.output_dir
        )
        self.assertEqual(new_zip_file_path, expected_new_zip_file_path)
        log_file_lines = []
        with open(self.log_file, "r") as open_file:
            for line in open_file:
                log_file_lines.append(line)

        self.assertEqual(log_file_lines[0], "%s starting to transform\n" % info_prefix)

        self.assertEqual(
            log_file_lines[1],
            "%s code_file_name: Figure 5source code 1.c\n" % info_prefix,
        )
        self.assertEqual(
            log_file_lines[2],
            (
                '%s from_file: ArticleZipFile("Figure 5source code 1.c",'
                ' "30-01-2019-RA-eLife-45644/Figure 5source code 1.c",'
                ' "tests/tmp/30-01-2019-RA-eLife-45644/Figure 5source code 1.c")\n'
            )
            % info_prefix,
        )

        self.assertEqual(
            log_file_lines[3],
            (
                '%s to_file: ArticleZipFile("Figure 5source code 1.c.zip",'
                ' "30-01-2019-RA-eLife-45644/Figure 5source code 1.c.zip",'
                ' "tests/tmp_output/Figure 5source code 1.c.zip")\n'
            )
            % info_prefix,
        )
        self.assertEqual(log_file_lines[4], "%s rewriting xml tags\n" % info_prefix)
        self.assertEqual(
            log_file_lines[5],
            (
                "%s writing xml to file"
                " tests/tmp/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml\n"
            )
            % info_prefix,
        )
        self.assertEqual(
            log_file_lines[6],
            (
                "%s writing new zip file"
                " tests/tmp_output/30-01-2019-RA-eLife-45644.zip\n"
            )
            % info_prefix,
        )
        # check output directory contents
        output_dir_list = os.listdir(self.output_dir)
        self.assertTrue("30-01-2019-RA-eLife-45644.zip" in output_dir_list)
        self.assertTrue("Figure 5source code 1.c.zip" in output_dir_list)

        # check zip file contents
        expected_infolist_filenames = [
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.pdf",
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
            "30-01-2019-RA-eLife-45644/Answers for the eLife digest.docx",
            "30-01-2019-RA-eLife-45644/Appendix 1.docx",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 1.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 12.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 13.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 14.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 15.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 2.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 3.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 4.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 5.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 6.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 7.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 8.png",
            "30-01-2019-RA-eLife-45644/Appendix 1figure 9.png",
            "30-01-2019-RA-eLife-45644/Figure 1.tif",
            "30-01-2019-RA-eLife-45644/Figure 2.tif",
            "30-01-2019-RA-eLife-45644/Figure 3.png",
            "30-01-2019-RA-eLife-45644/Figure 4.svg",
            "30-01-2019-RA-eLife-45644/Figure 4source data 1.zip",
            "30-01-2019-RA-eLife-45644/Figure 5.png",
            "30-01-2019-RA-eLife-45644/Figure 5source code 1.c.zip",
            "30-01-2019-RA-eLife-45644/Figure 6.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 10_HorC.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 1_U crassus.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 2_U pictorum.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 3_M margaritifera.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 4_P auricularius.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 5_PesB.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 6_HavA.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 7_HavB.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 8_HavC.png",
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 9_HorB.png",
            "30-01-2019-RA-eLife-45644/Figure 6source data 1.pdf",
            "30-01-2019-RA-eLife-45644/Manuscript.docx",
            "30-01-2019-RA-eLife-45644/Potential striking image.tif",
            "30-01-2019-RA-eLife-45644/Table 2source data 1.xlsx",
            "30-01-2019-RA-eLife-45644/transparent_reporting_Sakalauskaite.docx",
        ]
        with zipfile.ZipFile(new_zip_file_path, "r") as open_zipfile:
            infolist = open_zipfile.infolist()
        infolist_filenames = sorted(
            [info.filename for info in infolist if info.filename != ".keepme"]
        )
        self.assertEqual(infolist_filenames, expected_infolist_filenames)

        # assertions on XML file contents
        with zipfile.ZipFile(new_zip_file_path, "r") as open_zipfile:
            article_xml = open_zipfile.read(
                "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml"
            )
        self.assertTrue(
            b"<upload_file_nm>Figure 5source code 1.c.zip</upload_file_nm>"
            in article_xml
        )
        self.assertTrue(
            b"<upload_file_nm>Figure 5source code 1.c</upload_file_nm>"
            not in article_xml
        )

        # assertions on code zip file contents
        with zipfile.ZipFile(new_zip_file_path, "r") as open_zipfile:
            code_zip = open_zipfile.read(
                "30-01-2019-RA-eLife-45644/Figure 5source code 1.c.zip"
            )
        file_like_object = io.BytesIO(code_zip)
        with zipfile.ZipFile(file_like_object, "r") as open_zipfile:
            infolist = open_zipfile.infolist()
        self.assertEqual(
            [info.filename for info in infolist],
            ["30-01-2019-RA-eLife-45644/Figure 5source code 1.c"],
        )
        # self.assertTrue(False)


class TestXmlElementToString(unittest.TestCase):
    def test_xml_element_to_string(self):
        xml_string = (
            '<article article-type="research-article"'
            ' xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front><article-meta><permissions>"
            '<license license-type="open-access"'
            ' xlink:href="http://creativecommons.org/licenses/by/4.0/"/>'
            "</permissions></article-meta></front>"
            "</article>"
        )
        root = ElementTree.fromstring(xml_string)
        expected = '<?xml version="1.0" ?>%s' % xml_string
        self.assertEqual(transform.xml_element_to_string(root), expected)


class TestCodeFileList(unittest.TestCase):
    def test_code_file_list(self):
        xml_string = read_fixture("code_file_list.xml")
        expected = read_fixture("code_file_list.py")
        root = ElementTree.fromstring(xml_string)
        code_files = transform.code_file_list(root)
        self.assertEqual(code_files, expected)


class TestFindInFileNameMap(unittest.TestCase):
    def test_find_in_file_name_map(self):
        file_name = "file_one.txt"
        asset_file_name = "zip_sub_folder/file_one.txt"
        file_path = "local_folder/zip_sub_folder/file_one.txt"
        file_name_map = {asset_file_name: file_path}
        expected = (asset_file_name, file_path)
        self.assertEqual(
            transform.find_in_file_name_map(file_name, file_name_map), expected
        )

    def test_find_in_file_name_map_not_found(self):
        file_name = "file_one.txt"
        file_name_map = {}
        expected = (None, None)
        self.assertEqual(
            transform.find_in_file_name_map(file_name, file_name_map), expected
        )


class TestZipCodeFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_zip_code_file(self):
        file_name = "main.c"
        from_file = ArticleZipFile(
            file_name, "zip_folder/%s" % file_name, "tests/test_data/%s" % file_name
        )
        expected = ArticleZipFile(
            "%s.zip" % file_name,
            "zip_folder/%s.zip" % file_name,
            "%s/%s.zip" % (self.temp_dir, file_name),
        )
        to_file = transform.zip_code_file(from_file, self.temp_dir)
        # compare ArticleZipFile representation by casting them to str
        self.assertEqual(str(to_file), str(expected))


class TestFromFileToFileMap(unittest.TestCase):
    def test_from_file_to_file_map(self):
        from_xml_name = "source.c"
        to_xml_name = "source.c.zip"
        from_file = ArticleZipFile(from_xml_name, None, None)
        to_file = ArticleZipFile(to_xml_name, None, None)
        file_transformations = [(from_file, to_file)]
        expected = {from_xml_name: to_xml_name}
        self.assertEqual(
            transform.from_file_to_file_map(file_transformations), expected
        )


class TestTransformXmlFileTags(unittest.TestCase):
    def test_transform_xml_file_tags(self):
        # populate an ElementTree
        xml_string = read_fixture("code_file_list.xml")
        root = ElementTree.fromstring(xml_string)
        # specify from file, to file transformations
        file_transformations = []
        test_data = [
            {
                "from_xml": "Figure 5source code 1.c",
                "to_xml": "Figure 5source code 1.c.zip",
            },
            {
                "from_xml": "Figure 5source code 2.c",
                "to_xml": "Figure 5source code 2.c.zip",
            },
        ]
        for data in test_data:
            from_file = ArticleZipFile(data.get("from_xml"), None, None)
            to_file = ArticleZipFile(data.get("to_xml"), None, None)
            file_transformations.append((from_file, to_file))
        # invoke the function
        root_output = transform.transform_xml_file_tags(root, file_transformations)
        # find the tag in the XML root returned which will have been altered
        upload_file_nm_tags = root_output.findall(
            "./front/article-meta/files/file/upload_file_nm"
        )
        # assert the XML text is different
        self.assertEqual(upload_file_nm_tags[1].text, test_data[0].get("to_xml"))
        self.assertEqual(upload_file_nm_tags[2].text, test_data[1].get("to_xml"))


class TestTransformAssetFileNameMap(unittest.TestCase):
    def test_transform_asset_file_name_map_empty(self):
        # test empty arguments
        asset_file_name_map = {}
        file_transformations = []
        expected = {}
        new_asset_file_name_map = transform.transform_asset_file_name_map(
            asset_file_name_map, file_transformations
        )
        self.assertEqual(new_asset_file_name_map, expected)

    def test_transform_asset_file_name_map(self):
        # test one file example
        asset_file_name_map = {"zip_folder/main.c": "local_folder/zip_folder/main.c"}
        from_file = ArticleZipFile(
            "main.c", "zip_folder/main.c", "local_folder/zip_folder/main.c"
        )
        to_file = ArticleZipFile(
            "main.c.zip", "zip_folder/main.c.zip", "tmp_folder/zip_folder/main.c.zip"
        )
        file_transformations = [(from_file, to_file)]
        expected = {"zip_folder/main.c.zip": "tmp_folder/zip_folder/main.c.zip"}
        new_asset_file_name_map = transform.transform_asset_file_name_map(
            asset_file_name_map, file_transformations
        )
        self.assertEqual(new_asset_file_name_map, expected)

    def test_transform_asset_file_name_map_mismatch(self):
        # test if from_file is not found in the name map
        asset_file_name_map = {}
        from_file = ArticleZipFile(
            "main.c", "zip_folder/main.c", "local_folder/zip_folder/main.c"
        )
        to_file = ArticleZipFile(
            "main.c.zip", "zip_folder/main.c.zip", "tmp_folder/zip_folder/main.c.zip"
        )
        file_transformations = [(from_file, to_file)]
        expected = {}
        new_asset_file_name_map = transform.transform_asset_file_name_map(
            asset_file_name_map, file_transformations
        )
        self.assertEqual(new_asset_file_name_map, expected)


class TestCreateZipFromFileMap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_create_zip_from_file_map(self):
        zip_path = os.path.join(self.temp_dir, "test.zip")
        # add a file from the test data
        file_name = "zip_folder/main.c"
        file_path = "tests/test_data/main.c"
        file_name_map = {file_name: file_path}
        transform.create_zip_from_file_map(zip_path, file_name_map)
        with zipfile.ZipFile(zip_path, "r") as open_zipfile:
            infolist = open_zipfile.infolist()
        self.assertEqual(infolist[0].filename, file_name)