import os
import time
import unittest
from xml.etree import ElementTree
import json
from elifetools import xmlio
from elifecleaner import LOGGER, configure_logging, prc
from tests.helpers import delete_files_in_folder

# elife ISSN example of non-PRC journal-id tag values
NON_PRC_XML = (
    "<article><front><journal-meta>"
    '<journal-id journal-id-type="nlm-ta">elife</journal-id>'
    '<journal-id journal-id-type="hwp">eLife</journal-id>'
    '<journal-id journal-id-type="publisher-id">eLife</journal-id>'
    "<journal-title-group>"
    "<journal-title>eLife</journal-title>"
    "</journal-title-group>"
    '<issn pub-type="epub">2050-084X</issn>'
    "<publisher>"
    "<publisher-name>eLife Sciences Publications, Ltd</publisher-name>"
    "</publisher>"
    "</journal-meta></front></article>"
)

# PRC xml will have non-eLife journal-id tag text values
PRC_XML = (
    "<article><front><journal-meta>"
    '<journal-id journal-id-type="nlm-ta">foo</journal-id>'
    '<journal-id journal-id-type="hwp">foo</journal-id>'
    '<journal-id journal-id-type="publisher-id">foo</journal-id>'
    "<journal-title-group>"
    "<journal-title>eLife Reviewed Preprints </journal-title>"
    "</journal-title-group>"
    '<issn pub-type="epub">2050-084X</issn>'
    "<publisher>"
    "<publisher-name>elife-rp Sciences Publications, Ltd</publisher-name>"
    "</publisher>"
    "</journal-meta></front></article>"
)


class TestIsXmlPrc(unittest.TestCase):
    def test_is_xml_prc(self):
        "PRC XML will return true"
        root = ElementTree.fromstring(PRC_XML)
        self.assertTrue(prc.is_xml_prc(root))

    def test_is_xml_prc_false(self):
        "test non-PRC XML will return false"
        root = ElementTree.fromstring(NON_PRC_XML)
        self.assertEqual(prc.is_xml_prc(root), False)

    def test_is_xml_prc_incomplete(self):
        "incomplete XML will return false"
        root = ElementTree.fromstring("<root/>")
        self.assertEqual(prc.is_xml_prc(root), False)

    def test_is_xml_prc_elocation_id(self):
        "elocation-id value has already been changed on a PRC XML"
        root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<elocation-id>RP88273</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        self.assertEqual(prc.is_xml_prc(root), True)


class TestTransformJournalIdTags(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_transform_journal_id_tags(self):
        # populate an ElementTree
        identifier = "test.zip"
        xml_string = PRC_XML
        expected = bytes(NON_PRC_XML, encoding="utf-8")
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.transform_journal_id_tags(root, identifier)
        # assertions
        self.assertTrue(
            b'<journal-id journal-id-type="nlm-ta">elife</journal-id>'
            in ElementTree.tostring(root_output)
        )
        self.assertTrue(
            b'<journal-id journal-id-type="hwp">eLife</journal-id>'
            in ElementTree.tostring(root_output)
        )
        self.assertTrue(
            b'<journal-id journal-id-type="publisher-id">eLife</journal-id>'
            in ElementTree.tostring(root_output)
        )

        log_file_lines = []
        with open(self.log_file, "r") as open_file:
            for line in open_file:
                log_file_lines.append(line)
        for index, (journal_id_type, tag_text) in enumerate(
            [("nlm-ta", "elife"), ("hwp", "eLife"), ("publisher-id", "eLife")]
        ):
            self.assertEqual(
                log_file_lines[index],
                (
                    (
                        "INFO elifecleaner:prc:transform_journal_id_tags: "
                        "%s replacing journal-id tag text of type %s to %s\n"
                    )
                )
                % (identifier, journal_id_type, tag_text),
            )


class TestTransformJournalTitleTag(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_journal_title(self):
        # populate an ElementTree
        identifier = "test.zip"
        xml_string = PRC_XML
        tag_text = "eLife"
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.transform_journal_title_tag(root, identifier)
        # assertions
        self.assertTrue(
            b"<journal-title>%s</journal-title>" % bytes(tag_text, encoding="utf-8")
            in ElementTree.tostring(root_output)
        )
        log_file_lines = []
        with open(self.log_file, "r") as open_file:
            for line in open_file:
                log_file_lines.append(line)
        self.assertEqual(
            log_file_lines[-1],
            (
                (
                    "INFO elifecleaner:prc:transform_journal_meta_tag: "
                    "%s replacing journal-title tag text to %s\n"
                )
            )
            % (identifier, tag_text),
        )


class TestTransformPublisherNameTag(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_publisher_name(self):
        # populate an ElementTree
        identifier = "test.zip"
        xml_string = PRC_XML
        tag_text = "eLife Sciences Publications, Ltd"
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.transform_publisher_name_tag(root, identifier)
        # assertions
        self.assertTrue(
            b"<publisher-name>%s</publisher-name>" % bytes(tag_text, encoding="utf-8")
            in ElementTree.tostring(root_output)
        )
        log_file_lines = []
        with open(self.log_file, "r") as open_file:
            for line in open_file:
                log_file_lines.append(line)
        self.assertEqual(
            log_file_lines[-1],
            (
                (
                    "INFO elifecleaner:prc:transform_journal_meta_tag: "
                    "%s replacing publisher-name tag text to %s\n"
                )
            )
            % (identifier, tag_text),
        )


class TestAddPrcCustomMetaTags(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.expected_xml = bytes(
            "<article>"
            "<front>"
            "<article-meta>"
            "<custom-meta-group>"
            '<custom-meta specific-use="meta-only">'
            "<meta-name>publishing-route</meta-name>"
            "<meta-value>prc</meta-value>"
            "</custom-meta>"
            "</custom-meta-group>"
            "</article-meta>"
            "</front>"
            "</article>",
            encoding="utf-8",
        )

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_add_custom_meta_tags(self):
        "test when custom-meta-group tag does not yet exist"
        # populate an ElementTree
        xml_string = "<article><front><article-meta/></front></article>"
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.add_prc_custom_meta_tags(root)
        # assertions
        self.assertEqual(ElementTree.tostring(root_output), self.expected_xml)

    def test_group_tag_exists(self):
        "test if custom-meta-group tag already exists"
        # populate an ElementTree
        xml_string = (
            "<article><front><article-meta>"
            "<custom-meta-group />"
            "</article-meta></front></article>"
        )
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.add_prc_custom_meta_tags(root)
        # assertions
        self.assertEqual(ElementTree.tostring(root_output), self.expected_xml)

    def test_no_article_meta_tag(self):
        # populate an ElementTree
        identifier = "test.zip"
        xml_string = "<root/>"
        expected = b"<root />"
        root = ElementTree.fromstring(xml_string)
        # invoke the function
        root_output = prc.add_prc_custom_meta_tags(root, identifier)
        # assertions
        self.assertEqual(ElementTree.tostring(root_output), expected)
        with open(self.log_file, "r") as open_file:
            self.assertEqual(
                open_file.read(),
                (
                    "WARNING elifecleaner:prc:add_prc_custom_meta_tags: "
                    "%s article-meta tag not found\n"
                )
                % identifier,
            )


class TestElocationIdFromDocmap(unittest.TestCase):
    "tests for prc.elocation_id_from_docmap()"

    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_elocation_id_from_docmap(self):
        "get elocation-id from docmap data"
        docmap_json = docmap_test_data()
        expected = "RP85111"
        # invoke
        elocation_id = prc.elocation_id_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(elocation_id, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        self.assertEqual(
            log_messages[0],
            ("INFO elifecleaner:prc:elocation_id_from_docmap: " "Parse docmap json\n"),
        )

    def test_find_by_version_doi(self):
        "get elocation-id from docmap data by matching version DOI value"
        docmap_json = docmap_test_data()
        version_doi = "10.7554/eLife.85111.1"
        expected = "RP85111"
        # invoke
        elocation_id = prc.elocation_id_from_docmap(
            json.dumps(docmap_json), version_doi=version_doi, identifier=self.identifier
        )
        # assert
        self.assertEqual(elocation_id, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        self.assertEqual(
            log_messages[0],
            ("INFO elifecleaner:prc:elocation_id_from_docmap: " "Parse docmap json\n"),
        )

    def test_no_history_data(self):
        "test if no history data can be found in the docmap"
        docmap_json = {"first-step": "_:b0", "steps": {"_:b0": {}}}
        expected = None
        # invoke
        elocation_id = prc.elocation_id_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        # assert
        self.assertEqual(elocation_id, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:elocation_id_from_docmap: "
                    "%s no elocation_id found in the docmap\n"
                )
                % self.identifier,
            )

    def test_docmap_is_none(self):
        "test if docmap is empty"
        docmap_json = {}
        # invoke
        elocation_id = prc.elocation_id_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(elocation_id, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:elocation_id_from_docmap: "
                    "%s parsing docmap returned None\n"
                )
                % self.identifier,
            )


def docmap_test_data(doi=None):
    "generate a docmap json test fixture"
    docmap_json = {
        "first-step": "_:b0",
        "steps": {
            "_:b0": {
                "actions": [
                    {
                        "participants": [],
                        "outputs": [
                            {
                                "type": "preprint",
                                "identifier": "85111",
                                "doi": "10.7554/eLife.85111.1",
                                "versionIdentifier": "1",
                                "license": "http://creativecommons.org/licenses/by/4.0/",
                            }
                        ],
                    }
                ],
                "assertions": [
                    {
                        "item": {
                            "type": "preprint",
                            "doi": "10.1101/2022.11.08.515698",
                            "versionIdentifier": "2",
                        },
                        "status": "under-review",
                        "happened": "2022-11-28T11:30:05+00:00",
                    }
                ],
                "next-step": "_:b1",
            },
            "_:b1": {
                "actions": [
                    {
                        "outputs": [
                            {
                                "type": "preprint",
                                "identifier": "85111",
                                "versionIdentifier": "1",
                                "license": "http://creativecommons.org/licenses/by/4.0/",
                                "published": "2023-01-25T14:00:00+00:00",
                                "partOf": {
                                    "type": "manuscript",
                                    "doi": "10.7554/eLife.85111",
                                    "identifier": "85111",
                                    "subjectDisciplines": ["Neuroscience"],
                                    "published": "2023-01-25T14:00:00+00:00",
                                    "volumeIdentifier": "12",
                                    "electronicArticleIdentifier": "RP85111",
                                },
                            }
                        ]
                    },
                ]
            },
        },
    }
    if doi:
        # add doi key and value to the outputs
        docmap_json["steps"]["_:b1"]["actions"][0]["outputs"][0]["doi"] = doi
    return docmap_json


class TestVersionDoiFromDocmap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_version_doi_from_docmap(self):
        "test for when a doi is found"
        doi = "10.7554/eLife.85111.2"
        docmap_json = docmap_test_data(doi)
        result = prc.version_doi_from_docmap(json.dumps(docmap_json), self.identifier)
        self.assertEqual(result, doi)

    def test_unpublished_version_doi(self):
        "test argument published is False"
        doi = "10.7554/eLife.85111.2"
        docmap_json = docmap_test_data(doi)
        # delete the published dict key
        del docmap_json["steps"]["_:b1"]["actions"][0]["outputs"][0]["published"]
        result = prc.version_doi_from_docmap(
            json.dumps(docmap_json), self.identifier, False
        )
        self.assertEqual(result, doi)

    def test_docmap_is_none(self):
        "test for no docmap"
        docmap_json = {}
        result = prc.version_doi_from_docmap(json.dumps(docmap_json), self.identifier)
        self.assertEqual(result, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:version_doi_from_docmap: "
                    "%s parsing docmap returned None\n"
                )
                % self.identifier,
            )

    def test_no_preprint_in_docmap(self):
        "test for doi is not present"
        docmap_json = docmap_test_data(None)
        # delete the step holding the preprint data
        del docmap_json["steps"]["_:b1"]
        result = prc.version_doi_from_docmap(json.dumps(docmap_json), self.identifier)
        self.assertEqual(result, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:version_doi_from_docmap: "
                    "%s no preprint data was found in the docmap\n"
                )
                % self.identifier,
            )

    def test_no_doi_key_in_docmap(self):
        "test for doi is not present"
        docmap_json = docmap_test_data(None)
        result = prc.version_doi_from_docmap(json.dumps(docmap_json), self.identifier)
        self.assertEqual(result, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:version_doi_from_docmap: "
                    "%s did not find doi data in the docmap preprint data\n"
                )
                % self.identifier,
            )


class TestNextVersionDoi(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_next_version_doi(self):
        doi = "10.7554/eLife.85111.2"
        expected = "10.7554/eLife.85111.3"
        result = prc.next_version_doi(doi, self.identifier)
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "INFO elifecleaner:prc:next_version_doi: "
                    "%s next version doi, from DOI %s, next DOI %s\n"
                )
                % (self.identifier, doi, expected),
            )

    def test_non_int_version(self):
        "non-int version value at the end"
        version = "sa1"
        doi = "10.7554/eLife.85111.2.%s" % version
        expected = None
        result = prc.next_version_doi(doi, self.identifier)
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:next_version_doi: "
                    "%s version from DOI could not be converted to int, version %s\n"
                )
                % (self.identifier, version),
            )

    def test_version_exceeds_limit(self):
        "non-int version value at the end"
        article_id = "85111"
        doi = "10.7554/eLife.%s" % article_id
        expected = None
        result = prc.next_version_doi(doi, self.identifier)
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:next_version_doi: "
                    "%s failed to determine the version from DOI, "
                    "version %s exceeds MAX_VERSION %s\n"
                )
                % (self.identifier, article_id, prc.MAX_VERSION),
            )

    def test_none(self):
        "non-int version value at the end"
        doi = None
        expected = None
        result = prc.next_version_doi(doi, self.identifier)
        self.assertEqual(result, expected)


class TestAddArticleId(unittest.TestCase):
    "tests for add_article_id()"

    def test_add_article_id(self):
        "test adding concept DOI article-id tag"
        xml_string = "<article-meta />"
        root = ElementTree.fromstring(xml_string)
        doi = "10.7554/eLife.1234567890"
        pub_id_type = "doi"
        expected = (
            "<article-meta>"
            '<article-id pub-id-type="%s">%s</article-id>'
            "</article-meta>"
        ) % (pub_id_type, doi)
        prc.add_article_id(root, doi, pub_id_type)
        self.assertEqual(ElementTree.tostring(root).decode("utf-8"), expected)

    def test_version_doi(self):
        "test adding a version DOI article-id tag"
        xml_string = "<article-meta />"
        root = ElementTree.fromstring(xml_string)
        doi = "10.7554/eLife.1234567890"
        pub_id_type = "doi"
        specific_use = "version"
        expected = (
            "<article-meta>"
            '<article-id pub-id-type="%s" specific-use="%s">%s</article-id>'
            "</article-meta>"
        ) % (pub_id_type, specific_use, doi)
        prc.add_article_id(root, doi, pub_id_type, specific_use)
        self.assertEqual(ElementTree.tostring(root).decode("utf-8"), expected)


class TestAddVersionDoi(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.doi = "10.7554/eLife.1234567890.5"
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_add_version_doi(self):
        xml_string = "<article><front><article-meta /></front></article>"
        root = ElementTree.fromstring(xml_string)
        expected = (
            b"<article>"
            b"<front>"
            b"<article-meta>"
            b'<article-id pub-id-type="doi" specific-use="version">'
            b"10.7554/eLife.1234567890.5"
            b"</article-id>"
            b"</article-meta>"
            b"</front>"
            b"</article>"
        )
        root_output = prc.add_version_doi(root, self.doi, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_add_version_doi_in_order(self):
        "test the new article-id tag is added in a particular order"
        xml_string = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-id />"
            "<open-access>YES</open-access>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        root = ElementTree.fromstring(xml_string)
        expected = (
            b"<article>"
            b"<front>"
            b"<article-meta>"
            b"<article-id />"
            b'<article-id pub-id-type="doi" specific-use="version">'
            b"10.7554/eLife.1234567890.5"
            b"</article-id>"
            b"<open-access>YES</open-access>"
            b"</article-meta>"
            b"</front>"
            b"</article>"
        )
        root_output = prc.add_version_doi(root, self.doi, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_no_article_meta(self):
        "test if no article-meta tag is in the XML"
        xml_string = "<article />"
        root = ElementTree.fromstring(xml_string)
        expected = bytes(xml_string, encoding="utf-8")
        root_output = prc.add_version_doi(root, self.doi, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)
        with open(self.log_file, "r") as open_file:
            self.assertEqual(
                open_file.read(),
                ("WARNING elifecleaner:prc:add_doi: " "%s article-meta tag not found\n")
                % self.identifier,
            )


class TestReviewDateFromDocmap(unittest.TestCase):
    "tests for prc.review_date_from_docmap()"

    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_review_date_from_docmap(self):
        "test docmap which has a review date"
        docmap_json = docmap_test_data()
        expected = "2022-11-28T11:30:05+00:00"
        # invoke
        date_string = prc.review_date_from_docmap(json.dumps(docmap_json))
        # assert
        self.assertEqual(date_string, expected)

    def test_no_assertions(self):
        "test docmap which has a review date"
        docmap_json = docmap_test_data()
        # remove assertions from the test data
        del docmap_json["steps"]["_:b0"]["assertions"]
        expected = None
        # invoke
        date_string = prc.review_date_from_docmap(json.dumps(docmap_json))
        # assert
        self.assertEqual(date_string, expected)

    def test_docmap_is_none(self):
        "test for no docmap"
        docmap_json = {}
        result = prc.review_date_from_docmap(json.dumps(docmap_json), self.identifier)
        self.assertEqual(result, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:review_date_from_docmap: "
                    "%s parsing docmap returned None\n"
                )
                % self.identifier,
            )


class TestLicenseFromDocmap(unittest.TestCase):
    "tests for license_from_docmap()"

    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_license_from_docmap(self):
        "parse license from docmap preprint output"
        docmap_json = docmap_test_data()
        expected = "http://creativecommons.org/licenses/by/4.0/"
        # invoke
        result = prc.license_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        self.assertEqual(
            log_messages[0],
            ("INFO elifecleaner:prc:license_from_docmap: " "Parse docmap json\n"),
        )

    def test_no_license(self):
        "test if no license data can be found in the docmap"
        docmap_json = docmap_test_data()
        del docmap_json["steps"]["_:b1"]["actions"][0]["outputs"][0]["license"]
        expected = None
        # invoke
        result = prc.license_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        # assert
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:license_from_docmap: "
                    "%s no license found in the docmap\n"
                )
                % self.identifier,
            )

    def test_docmap_is_none(self):
        "test if docmap is empty"
        docmap_json = {}
        # invoke
        result = prc.license_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(result, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:license_from_docmap: "
                    "%s parsing docmap returned None\n"
                )
                % self.identifier,
            )


class TestVolumeFromDocmap(unittest.TestCase):
    "tests for prc.volume_from_docmap()"

    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_volume_from_docmap(self):
        "parse volume from docmap data"
        docmap_json = docmap_test_data()
        expected = 12
        # invoke
        volume = prc.volume_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(volume, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        self.assertEqual(
            log_messages[0],
            ("INFO elifecleaner:prc:volume_from_docmap: " "Parse docmap json\n"),
        )

    def test_volume_non_int(self):
        "test if the volume value cannot be parsed to int"
        docmap_json = docmap_test_data()
        docmap_json["steps"]["_:b1"]["actions"][0]["outputs"][0]["partOf"][
            "volumeIdentifier"
        ] = "foo"
        expected = None
        # invoke
        volume = prc.volume_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(volume, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        self.assertEqual(
            log_messages[0],
            ("INFO elifecleaner:prc:volume_from_docmap: " "Parse docmap json\n"),
        )
        self.assertEqual(
            log_messages[-1],
            (
                "WARNING elifecleaner:prc:volume_from_docmap: "
                "test.zip volume from the docmap could not be cast as int\n"
            ),
        )

    def test_no_history_data(self):
        "test if no history data can be found in the docmap"
        docmap_json = {"first-step": "_:b0", "steps": {"_:b0": {}}}
        expected = None
        # invoke
        volume = prc.volume_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        # assert
        self.assertEqual(volume, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:volume_from_docmap: "
                    "%s no volume found in the docmap\n"
                )
                % self.identifier,
            )

    def test_docmap_is_none(self):
        "test if docmap is empty"
        docmap_json = {}
        # invoke
        volume = prc.volume_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(volume, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:volume_from_docmap: "
                    "%s parsing docmap returned None\n"
                )
                % self.identifier,
            )


class TestArticleCategoriesFromDocmap(unittest.TestCase):
    "tests for article_categories_from_docmap()"

    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_article_categories(self):
        "parse article categories from docmap preprint output"
        docmap_json = docmap_test_data()
        expected = ["Neuroscience"]
        # invoke
        result = prc.article_categories_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        self.assertEqual(
            log_messages[0],
            (
                "INFO elifecleaner:prc:article_categories_from_docmap: "
                "Parse docmap json\n"
            ),
        )

    def test_no_article_categories(self):
        "test if no article categories data can be found in the docmap"
        docmap_json = docmap_test_data()
        del docmap_json["steps"]["_:b1"]["actions"][0]["outputs"][0]["partOf"]
        expected = None
        # invoke
        result = prc.article_categories_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
        # assert
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:article_categories_from_docmap: "
                    "%s no article_categories found in the docmap\n"
                )
                % self.identifier,
            )

    def test_docmap_is_none(self):
        "test if docmap is empty"
        docmap_json = {}
        # invoke
        result = prc.article_categories_from_docmap(
            json.dumps(docmap_json), identifier=self.identifier
        )
        # assert
        self.assertEqual(result, None)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "WARNING elifecleaner:prc:article_categories_from_docmap: "
                    "%s parsing docmap returned None\n"
                )
                % self.identifier,
            )


class TestDateStructFromString(unittest.TestCase):
    "tests for prc.date_struct_from_string()"

    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.identifier = "test.zip"

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_with_timezone(self):
        "test docmap which has a review date"
        date_string = "2022-11-28T11:30:05+00:00"
        expected = time.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
        result = prc.date_struct_from_string(date_string)
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "INFO elifecleaner:prc:date_struct_from_string: "
                    'unable to parse "%s" using format "%s"\n'
                )
                % (date_string, "%Y-%m-%dT%H:%M:%S.%f%z"),
            )

    def test_date(self):
        "test docmap which has a review date"
        date_string = "2022-11-28"
        expected = time.strptime(date_string, "%Y-%m-%d")
        result = prc.date_struct_from_string(date_string)
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[-1],
                (
                    "INFO elifecleaner:prc:date_struct_from_string: "
                    'unable to parse "%s" using format "%s"\n'
                )
                % (date_string, "%Y-%m-%dT%H:%M:%S%z"),
            )

    def test_with_microtime(self):
        "test docmap which has a review date"
        date_string = "2022-11-28T11:30:05.579531+00:00"
        expected = time.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f%z")
        result = prc.date_struct_from_string(date_string)
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(log_messages, [])

    def test_not_a_date(self):
        "test docmap which has a review date"
        date_string = "not_a_date"
        expected = None
        result = prc.date_struct_from_string(date_string)
        self.assertEqual(result, expected)
        with open(self.log_file, "r") as open_file:
            log_messages = open_file.readlines()
            self.assertEqual(
                log_messages[0],
                (
                    "INFO elifecleaner:prc:date_struct_from_string: "
                    'unable to parse "%s" using format "%s"\n'
                )
                % (date_string, "%Y-%m-%dT%H:%M:%S.%f%z"),
            )


class TestAddHistoryDate(unittest.TestCase):
    "tests for prc.add_history_date()"

    def setUp(self):
        self.xml_string_template = (
            "<article><front><article-meta>%s</article-meta></front></article>"
        )
        self.date_type = "sent-for-review"
        date_string = "2022-11-28"
        self.date_struct = time.strptime(date_string, "%Y-%m-%d")
        self.identifier = "test.zip"
        # expected history XML string for when using the input values
        self.history_xml_output = (
            "<history>"
            '<date date-type="sent-for-review">'
            "<day>28</day>"
            "<month>11</month>"
            "<year>2022</year>"
            "</date>"
            "</history>"
        )

    def test_add_history_date(self):
        "test adding a date to an existing history tag"
        xml_string = self.xml_string_template % "<history />"
        expected = bytes(
            self.xml_string_template % self.history_xml_output, encoding="utf-8"
        )
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_history_date(
            root, self.date_type, self.date_struct, self.identifier
        )
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_no_history_tag(self):
        "test if there is no history tag"
        xml_string = self.xml_string_template % ""
        expected = bytes(
            self.xml_string_template % self.history_xml_output, encoding="utf-8"
        )
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_history_date(
            root, self.date_type, self.date_struct, self.identifier
        )
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_elocation_id_tag(self):
        "test history tag should be added after the elocation-id tag"
        xml_string = self.xml_string_template % "<elocation-id />"
        expected = bytes(
            self.xml_string_template % ("<elocation-id />" + self.history_xml_output),
            encoding="utf-8",
        )
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_history_date(
            root, self.date_type, self.date_struct, self.identifier
        )
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_no_article_meta(self):
        "test if there is no article-meta tag"
        xml_string = "<article />"
        expected = b"<article />"
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_history_date(
            root, self.date_type, self.date_struct, self.identifier
        )
        self.assertEqual(ElementTree.tostring(root_output), expected)


class TestAddPubHistory(unittest.TestCase):
    "tests for prc.add_pub_history()"

    def setUp(self):
        # register XML namespaces
        xmlio.register_xmlns()

        self.xml_string_template = '<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta>%s</article-meta></front></article>'
        self.history_data = [
            {
                "type": "preprint",
                "date": "2022-11-22",
                "doi": "10.1101/2022.11.08.515698",
                "url": "https://www.biorxiv.org/content/10.1101/2022.11.08.515698v2",
                "versionIdentifier": "2",
                "published": "2022-11-22",
                "content": [
                    {
                        "type": "computer-file",
                        "url": "s3://transfers-elife/biorxiv_Current_Content/November_2022/23_Nov_22_Batch_1444/b0f4d90b-6c92-1014-9a2e-aae015926ab4.meca",
                    }
                ],
            },
            {
                "type": "reviewed-preprint",
                "date": "2023-01-25T14:00:00+00:00",
                "identifier": "85111",
                "doi": "10.7554/eLife.85111.1",
                "versionIdentifier": "1",
                "license": "http://creativecommons.org/licenses/by/4.0/",
                "published": "2023-01-25T14:00:00+00:00",
            },
            {
                "type": "reviewed-preprint",
                "date": "2023-05-10T14:00:00+00:00",
                "identifier": "85111",
                "doi": "10.7554/eLife.85111.2",
                "versionIdentifier": "2",
                "license": "http://creativecommons.org/licenses/by/4.0/",
                "published": "2023-05-10T14:00:00+00:00",
            },
        ]
        self.identifier = "test.zip"
        # expected history XML string for when using the input values
        self.xml_output = (
            "<pub-history>"
            "<event>"
            "<event-desc>This manuscript was published as a preprint.</event-desc>"
            '<date date-type="preprint" iso-8601-date="2022-11-22">'
            "<day>22</day>"
            "<month>11</month>"
            "<year>2022</year>"
            "</date>"
            '<self-uri content-type="preprint" xlink:href="https://doi.org/10.1101/2022.11.08.515698" />'
            "</event>"
            "<event>"
            "<event-desc>This manuscript was published as a reviewed preprint.</event-desc>"
            '<date date-type="reviewed-preprint" iso-8601-date="2023-01-25">'
            "<day>25</day>"
            "<month>01</month>"
            "<year>2023</year>"
            "</date>"
            '<self-uri content-type="reviewed-preprint" xlink:href="https://doi.org/10.7554/eLife.85111.1" />'
            "</event>"
            "<event>"
            "<event-desc>The reviewed preprint was revised.</event-desc>"
            '<date date-type="reviewed-preprint" iso-8601-date="2023-05-10">'
            "<day>10</day>"
            "<month>05</month>"
            "<year>2023</year>"
            "</date>"
            '<self-uri content-type="reviewed-preprint" xlink:href="https://doi.org/10.7554/eLife.85111.2" />'
            "</event>"
            "</pub-history>"
        )

    def test_add_pub_history(self):
        "test adding to an existing pub-history tag"
        xml_string = self.xml_string_template % "<pub-history />"
        expected = bytes(self.xml_string_template % self.xml_output, encoding="utf-8")
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_pub_history(root, self.history_data, self.identifier)
        print(ElementTree.tostring(root_output))
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_no_data(self):
        "test for if there is no data to be added"
        # use xlink:href in the sample and the xmlns is kept in the output
        xml_string = (
            self.xml_string_template % '<ext-link xlink:href="https://example.org" />'
        )
        history_data = None
        expected = bytes(xml_string, encoding="utf-8")
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_pub_history(root, history_data, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_after_history_tag(self):
        "test adding a pub-history tag after an existing history tag"
        xml_string = self.xml_string_template % "<history />"
        expected = bytes(
            self.xml_string_template % ("<history />" + self.xml_output),
            encoding="utf-8",
        )
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_pub_history(root, self.history_data, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_elocation_id_tag(self):
        "test pub-history tag should be added after the elocation-id tag"
        xml_string = self.xml_string_template % "<elocation-id />"
        expected = bytes(
            self.xml_string_template % ("<elocation-id />" + self.xml_output),
            encoding="utf-8",
        )
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_pub_history(root, self.history_data, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_no_article_meta(self):
        "test if there is no article-meta tag"
        xml_string = "<article />"
        expected = b"<article />"
        root = ElementTree.fromstring(xml_string)
        root_output = prc.add_pub_history(root, self.history_data, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)
