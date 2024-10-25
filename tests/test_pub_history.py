import unittest
from xml.etree import ElementTree
from mock import patch
from elifetools import xmlio
from elifecleaner import pub_history
from tests.helpers import read_fixture

SCIETY_DATA = {
    "https://sciety.org/evaluations/hypothesis:6wCSiENREe-fsV9XrL_PJA/content": (
        b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Author response:"
    ),
    "https://sciety.org/evaluations/hypothesis:63fsPkNREe-RHzPeZyV9vQ/content": (
        b"<p><strong>%s</strong></p>\n"
        b"<p>The ....</p>\n" % b"Reviewer #3 (Public Review):"
    ),
    "https://sciety.org/evaluations/hypothesis:6-3XyENREe-rjbPoWNzSvw/content": (
        b"<p><strong>%s</strong></p>\n"
        b"<p>The ....</p>\n" % b"Reviewer #2 (Public Review):"
    ),
    "https://sciety.org/evaluations/hypothesis:7GBk0kNREe-LnVes3-n_9Q/content": (
        b"<p><strong>%s</strong></p>\n"
        b"<p>The ....</p>\n" % b"Reviewer #1 (Public Review):"
    ),
    "https://sciety.org/evaluations/hypothesis:7NzOvkNREe-fshsElWV5TQ/content": (
        b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"eLife assessment"
    ),
}


def mock_get_web_content(
    url=None,
):
    "return a content containing the response data based on the URL"
    if url and url in SCIETY_DATA:
        return SCIETY_DATA.get(url)
    # default
    return b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"


class TestPruneHistoryData(unittest.TestCase):
    "tests for prune_history_data()"

    def test_prune_history_data(self):
        "test removing history data of newer DOI versions"
        history_data = [
            {"doi": "preprint", "versionIdentifier": 2},
            {"doi": "10.7554/eLife.99854.1", "versionIdentifier": 1},
            {"doi": "10.7554/eLife.99854.2", "versionIdentifier": 2},
            {"doi": "10.7554/eLife.99854.3", "versionIdentifier": 3},
        ]
        doi = "10.7554/eLife.99854"
        version = 3
        expected = history_data[0:3]
        # invoke
        result = pub_history.prune_history_data(history_data, doi, version)
        # assert
        self.assertEqual(result, expected)


class TestFindPubHistoryTag(unittest.TestCase):
    "tests for find_pub_history_tag()"

    def test_find_pub_history_tag(self):
        "test finding pub-history tag from XML"
        xml_string = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<pub-history />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        root = ElementTree.fromstring(xml_string)
        identifier = "identifier"
        expected = "<pub-history />"
        # invoke
        result = pub_history.find_pub_history_tag(root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf-8"), expected)

    def test_history_tag(self):
        "test if history tag is in XML"
        xml_string = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<history />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        root = ElementTree.fromstring(xml_string)
        identifier = "identifier"
        expected = "<pub-history />"
        # invoke
        result = pub_history.find_pub_history_tag(root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf-8"), expected)

    def test_elocation_id_tag(self):
        "test if elocation-id tag is in XML"
        xml_string = (
            "<article>"
            "<front><article-meta><elocation-id /></article-meta></front></article>"
        )
        root = ElementTree.fromstring(xml_string)
        identifier = "identifier"
        expected = "<pub-history />"
        # invoke
        result = pub_history.find_pub_history_tag(root, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf-8"), expected)

    def test_no_article_meta(self):
        "test no article-meta tag in XML"
        xml_string = "<article />"
        root = ElementTree.fromstring(xml_string)
        identifier = "identifier"
        expected = None
        # invoke
        result = pub_history.find_pub_history_tag(root, identifier)
        # assert
        self.assertEqual(result, expected)


class TestAddSelfUriTag(unittest.TestCase):
    "tests for add_self_uri_tag()"

    def test_add_self_uri_tag(self):
        "test adding self-uri tag"
        xmlio.register_xmlns()
        parent = ElementTree.fromstring("<root />")
        article_type = "preprint"
        uri = "https://example.org/"
        title = "A self URI"
        expected = (
            '<root xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<self-uri content-type="preprint" xlink:href="https://example.org/">'
            "A self URI"
            "</self-uri>"
            "</root>"
        )
        # invoke
        pub_history.add_self_uri_tag(parent, article_type, uri, title)
        # assert
        self.assertEqual(ElementTree.tostring(parent).decode("utf-8"), expected)


class TestAddHistoryEventTag(unittest.TestCase):
    "tests for add_history_event_tag()"

    def test_add_history_event_tag(self):
        "test adding event tag with examples of all content"
        xmlio.register_xmlns()
        parent = ElementTree.fromstring("<root />")
        event_data = {
            "event_desc": "Preprint posted",
            "type": "preprint",
            "doi": "https://example.org/doi",
            "date": "2024-10-21",
            "self_uri_list": [
                {
                    "content_type": "editor-report",
                    "uri": "https://example.org/",
                    "title": "eLife assessment",
                }
            ],
        }
        expected = (
            '<root xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<event>"
            "<event-desc>Preprint posted</event-desc>"
            '<date date-type="preprint" iso-8601-date="2024-10-21">'
            "<day>21</day>"
            "<month>10</month>"
            "<year>2024</year>"
            "</date>"
            '<self-uri content-type="preprint"'
            ' xlink:href="https://doi.org/https://example.org/doi" />'
            '<self-uri content-type="editor-report"'
            ' xlink:href="https://example.org/">eLife assessment</self-uri>'
            "</event>"
            "</root>"
        )
        # invoke
        pub_history.add_history_event_tag(parent, event_data)
        # assert
        self.assertEqual(ElementTree.tostring(parent).decode("utf-8"), expected)


class TestPreprintEventDesc(unittest.TestCase):
    "tests for preprint_event_desc()"

    def test_accepted_style(self):
        "test accepted style"
        style = "accepted"
        expected = "This manuscript was published as a preprint."
        # invoke
        result = pub_history.preprint_event_desc(style)
        # assert
        self.assertEqual(result, expected)

    def test_meca_style(self):
        "test meca style"
        style = "meca"
        expected = "Preprint posted"
        # invoke
        result = pub_history.preprint_event_desc(style)
        # assert
        self.assertEqual(result, expected)

    def test_none(self):
        "test style None"
        style = None
        expected = None
        # invoke
        result = pub_history.preprint_event_desc(style)
        # assert
        self.assertEqual(result, expected)


class TestReviewedPreprintEventDesc(unittest.TestCase):
    "tests for reviewed_preprint_event_desc()"

    def test_accepted_style_first_1(self):
        "test accepted style version 1 first event"
        style = "accepted"
        first_review_event = True
        version = 1
        expected = "This manuscript was published as a reviewed preprint."
        # invoke
        result = pub_history.reviewed_preprint_event_desc(
            style, first_review_event, version
        )
        # assert
        self.assertEqual(result, expected)

    def test_accepted_style_not_first_2(self):
        "test accepted style version 2 not first event"
        style = "accepted"
        first_review_event = False
        version = 2
        expected = "The reviewed preprint was revised."
        # invoke
        result = pub_history.reviewed_preprint_event_desc(
            style, first_review_event, version
        )
        # assert
        self.assertEqual(result, expected)

    def test_meca_style_first_1(self):
        "test meca style version 1 first event"
        style = "meca"
        first_review_event = True
        version = 1
        expected = "Reviewed preprint v1"
        # invoke
        result = pub_history.reviewed_preprint_event_desc(
            style, first_review_event, version
        )
        # assert
        self.assertEqual(result, expected)

    def test_meca_style_not_first_2(self):
        "test meca style version 1 first event"
        style = "meca"
        first_review_event = False
        version = 2
        expected = "Reviewed preprint v2"
        # invoke
        result = pub_history.reviewed_preprint_event_desc(
            style, first_review_event, version
        )
        # assert
        self.assertEqual(result, expected)

    def test_none(self):
        "test style None"
        style = None
        first_review_event = None
        version = None
        expected = None
        # invoke
        result = pub_history.reviewed_preprint_event_desc(
            style, first_review_event, version
        )
        # assert
        self.assertEqual(result, expected)


class TestHistoryEventSelfUriList(unittest.TestCase):
    "tests for history_event_self_uri_list()"

    @patch("docmaptools.parse.get_web_content")
    def test_self_uri_list(self, fake_get):
        "test get self-uri data from docmap"
        fake_get.side_effect = mock_get_web_content
        docmap_string = read_fixture("99854.json", mode="r")
        version_doi = "10.7554/eLife.99854.1"
        expected = [
            {
                "content_type": "editor-report",
                "uri": "https://doi.org/10.7554/eLife.99854.1.sa4",
                "title": "eLife assessment",
            },
            {
                "content_type": "referee-report",
                "uri": "https://doi.org/10.7554/eLife.99854.1.sa3",
                "title": "Reviewer #1 (Public Review):",
            },
            {
                "content_type": "referee-report",
                "uri": "https://doi.org/10.7554/eLife.99854.1.sa2",
                "title": "Reviewer #2 (Public Review):",
            },
            {
                "content_type": "referee-report",
                "uri": "https://doi.org/10.7554/eLife.99854.1.sa1",
                "title": "Reviewer #3 (Public Review):",
            },
            {
                "content_type": "author-comment",
                "uri": "https://doi.org/10.7554/eLife.99854.1.sa0",
                "title": "Author response:",
            },
        ]
        # invoke
        result = pub_history.history_event_self_uri_list(docmap_string, version_doi)
        # assert
        self.assertEqual(result, expected)


HISTORY_DATA_99854 = [
    {
        "type": "preprint",
        "date": "2024-04-27",
        "doi": "10.1101/2024.04.25.591185",
        "url": "https://www.biorxiv.org/content/10.1101/2024.04.25.591185v1",
        "versionIdentifier": "1",
        "published": "2024-04-27",
        "content": [
            {
                "type": "computer-file",
                "url": "s3://prod-elife-epp-meca/99854-v1-meca.zip",
            }
        ],
    },
    {
        "type": "reviewed-preprint",
        "date": "2024-07-17T14:00:00+00:00",
        "identifier": "99854",
        "doi": "10.7554/eLife.99854.1",
        "versionIdentifier": "1",
        "license": "http://creativecommons.org/licenses/by/4.0/",
        "published": "2024-07-17T14:00:00+00:00",
        "partOf": {
            "type": "manuscript",
            "doi": "10.7554/eLife.99854",
            "identifier": "99854",
            "subjectDisciplines": ["Structural Biology and Molecular Biophysics"],
            "published": "2024-07-17T14:00:00+00:00",
            "volumeIdentifier": "13",
            "electronicArticleIdentifier": "RP99854",
            "complement": [],
        },
    },
    {
        "type": "reviewed-preprint",
        "date": "2024-07-18T14:00:00+00:00",
        "identifier": "99854",
        "doi": "10.7554/eLife.99854.2",
        "versionIdentifier": "2",
        "license": "http://creativecommons.org/licenses/by/4.0/",
        "published": "2024-07-18T14:00:00+00:00",
        "partOf": {
            "type": "manuscript",
            "doi": "10.7554/eLife.99854",
            "identifier": "99854",
            "subjectDisciplines": ["Structural Biology and Molecular Biophysics"],
            "published": "2024-07-18T14:00:00+00:00",
            "volumeIdentifier": "13",
            "electronicArticleIdentifier": "RP99854",
            "complement": [],
        },
    },
]


class TestCollectHistoryEventData(unittest.TestCase):
    "tests for collect_history_event_data()"

    def test_accepted(self):
        "test collecting history data for accepted style"
        history_data = [
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
                        "url": (
                            "s3://transfers-elife/biorxiv_Current_Content/November_2022/"
                            "23_Nov_22_Batch_1444/b0f4d90b-6c92-1014-9a2e-aae015926ab4.meca"
                        ),
                    }
                ],
            },
        ]
        style = "accepted"
        docmap_string = read_fixture("99854.json", mode="r")
        add_self_uri = False
        expected = [
            {
                "type": "preprint",
                "date": "2022-11-22",
                "doi": "10.1101/2022.11.08.515698",
                "versionIdentifier": "2",
                "event_desc": "This manuscript was published as a preprint.",
            }
        ]
        # invoke
        result = pub_history.collect_history_event_data(
            history_data, style, docmap_string, add_self_uri
        )
        # assert
        self.assertEqual(len(result), 1)
        self.assertDictEqual(result[0], expected[0])

    @patch("docmaptools.parse.get_web_content")
    def test_meca(self, fake_get):
        "test collecting history data for meca style including self-uri data"
        fake_get.side_effect = mock_get_web_content
        style = "meca"
        docmap_string = read_fixture("99854.json", mode="r")
        add_self_uri = True
        expected = [
            {
                "type": "preprint",
                "date": "2024-04-27",
                "doi": "10.1101/2024.04.25.591185",
                "versionIdentifier": "1",
                "event_desc": "Preprint posted",
                "self_uri_list": [],
            },
            {
                "type": "reviewed-preprint",
                "date": "2024-07-17T14:00:00+00:00",
                "doi": "10.7554/eLife.99854.1",
                "versionIdentifier": "1",
                "event_desc": "Reviewed preprint v1",
                "self_uri_list": [
                    {
                        "content_type": "editor-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa4",
                        "title": "eLife assessment",
                    },
                    {
                        "content_type": "referee-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa3",
                        "title": "Reviewer #1 (Public Review):",
                    },
                    {
                        "content_type": "referee-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa2",
                        "title": "Reviewer #2 (Public Review):",
                    },
                    {
                        "content_type": "referee-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa1",
                        "title": "Reviewer #3 (Public Review):",
                    },
                    {
                        "content_type": "author-comment",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa0",
                        "title": "Author response:",
                    },
                ],
            },
        ]
        # invoke
        result = pub_history.collect_history_event_data(
            HISTORY_DATA_99854[0:2], style, docmap_string, add_self_uri
        )
        # assert
        self.assertEqual(len(result), 2)
        self.assertDictEqual(result[0], expected[0])
        self.assertDictEqual(result[1], expected[1])

    def test_no_history_data(self):
        "test if no history data supplied"
        history_data = []
        expected = []
        # invoke
        result = pub_history.collect_history_event_data(history_data, None, None, None)
        # assert
        self.assertEqual(result, expected)


class TestAddPubHistoryTag(unittest.TestCase):
    "tests for add_pub_history_tag()"

    def test_add_pub_history_tag(self):
        "test adding pub-history tag"
        root = ElementTree.fromstring(
            "<article><front><article-meta /></front></article>"
        )
        history_event_data = [
            {
                "type": "preprint",
                "date": "2022-11-22",
                "doi": "10.1101/2022.11.08.515698",
                "versionIdentifier": "2",
                "event_desc": "Preprint posted",
                "self_uri_list": [],
            },
            {
                "type": "reviewed-preprint",
                "date": "2024-07-17T14:00:00+00:00",
                "doi": "10.7554/eLife.99854.1",
                "versionIdentifier": "1",
                "event_desc": "Reviewed preprint v1",
                "self_uri_list": [
                    {
                        "content_type": "editor-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa4",
                        "title": "eLife assessment",
                    },
                    {
                        "content_type": "referee-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa3",
                        "title": "Reviewer #1 (Public Review):",
                    },
                    {
                        "content_type": "referee-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa2",
                        "title": "Reviewer #2 (Public Review):",
                    },
                    {
                        "content_type": "referee-report",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa1",
                        "title": "Reviewer #3 (Public Review):",
                    },
                    {
                        "content_type": "author-comment",
                        "uri": "https://doi.org/10.7554/eLife.99854.1.sa0",
                        "title": "Author response:",
                    },
                ],
            },
        ]
        identifier = "identifier"
        expected = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>"
            "<pub-history>"
            "<event>"
            "<event-desc>Preprint posted</event-desc>"
            '<date date-type="preprint" iso-8601-date="2022-11-22">'
            "<day>22</day>"
            "<month>11</month>"
            "<year>2022</year>"
            "</date>"
            '<self-uri content-type="preprint"'
            ' xlink:href="https://doi.org/10.1101/2022.11.08.515698" />'
            "</event>"
            "<event>"
            "<event-desc>Reviewed preprint v1</event-desc>"
            '<date date-type="reviewed-preprint" iso-8601-date="2024-07-17">'
            "<day>17</day>"
            "<month>07</month>"
            "<year>2024</year>"
            "</date>"
            '<self-uri content-type="reviewed-preprint"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1" />'
            '<self-uri content-type="editor-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa4">'
            "eLife assessment"
            "</self-uri>"
            '<self-uri content-type="referee-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa3">'
            "Reviewer #1 (Public Review):"
            "</self-uri>"
            '<self-uri content-type="referee-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa2">'
            "Reviewer #2 (Public Review):"
            "</self-uri>"
            '<self-uri content-type="referee-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa1">'
            "Reviewer #3 (Public Review):"
            "</self-uri>"
            '<self-uri content-type="author-comment"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa0">'
            "Author response:"
            "</self-uri>"
            "</event>"
            "</pub-history>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        result = pub_history.add_pub_history_tag(root, history_event_data, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf-8"), expected)

    def test_no_pub_history_tag(self):
        "test if no pub-history tag can be found or added"
        root = ElementTree.fromstring("<root />")
        history_event_data = [{"foo": "bar"}]
        identifier = "identifier"
        expected = "<root />"
        # invoke
        result = pub_history.add_pub_history_tag(root, history_event_data, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf-8"), expected)

    def test_no_history_data(self):
        "test if no history event data is supplied"
        root = ElementTree.fromstring("<root />")
        history_event_data = []
        identifier = "identifier"
        expected = "<root />"
        # invoke
        result = pub_history.add_pub_history_tag(root, history_event_data, identifier)
        # assert
        self.assertEqual(ElementTree.tostring(result).decode("utf-8"), expected)


class TestAddPubHistory(unittest.TestCase):
    "tests for prc.add_pub_history()"

    def setUp(self):
        # register XML namespaces
        xmlio.register_xmlns()

        self.xml_string_template = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>%s</article-meta>"
            "</front>"
            "</article>"
        )
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
                        "url": (
                            "s3://transfers-elife/biorxiv_Current_Content/November_2022/"
                            "23_Nov_22_Batch_1444/b0f4d90b-6c92-1014-9a2e-aae015926ab4.meca"
                        ),
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
            '<self-uri content-type="preprint"'
            ' xlink:href="https://doi.org/10.1101/2022.11.08.515698" />'
            "</event>"
            "<event>"
            "<event-desc>This manuscript was published as a reviewed preprint.</event-desc>"
            '<date date-type="reviewed-preprint" iso-8601-date="2023-01-25">'
            "<day>25</day>"
            "<month>01</month>"
            "<year>2023</year>"
            "</date>"
            '<self-uri content-type="reviewed-preprint"'
            ' xlink:href="https://doi.org/10.7554/eLife.85111.1" />'
            "</event>"
            "<event>"
            "<event-desc>The reviewed preprint was revised.</event-desc>"
            '<date date-type="reviewed-preprint" iso-8601-date="2023-05-10">'
            "<day>10</day>"
            "<month>05</month>"
            "<year>2023</year>"
            "</date>"
            '<self-uri content-type="reviewed-preprint"'
            ' xlink:href="https://doi.org/10.7554/eLife.85111.2" />'
            "</event>"
            "</pub-history>"
        )

    def test_add_pub_history(self):
        "test adding to an existing pub-history tag"
        xml_string = self.xml_string_template % "<pub-history />"
        expected = bytes(self.xml_string_template % self.xml_output, encoding="utf-8")
        root = ElementTree.fromstring(xml_string)
        root_output = pub_history.add_pub_history(
            root, self.history_data, self.identifier
        )
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
        root_output = pub_history.add_pub_history(root, history_data, self.identifier)
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_after_history_tag(self):
        "test adding a pub-history tag after an existing history tag"
        xml_string = self.xml_string_template % "<history />"
        expected = bytes(
            self.xml_string_template % ("<history />" + self.xml_output),
            encoding="utf-8",
        )
        root = ElementTree.fromstring(xml_string)
        root_output = pub_history.add_pub_history(
            root, self.history_data, self.identifier
        )
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_elocation_id_tag(self):
        "test pub-history tag should be added after the elocation-id tag"
        xml_string = self.xml_string_template % "<elocation-id />"
        expected = bytes(
            self.xml_string_template % ("<elocation-id />" + self.xml_output),
            encoding="utf-8",
        )
        root = ElementTree.fromstring(xml_string)
        root_output = pub_history.add_pub_history(
            root, self.history_data, self.identifier
        )
        self.assertEqual(ElementTree.tostring(root_output), expected)

    def test_no_article_meta(self):
        "test if there is no article-meta tag"
        xml_string = "<article />"
        expected = b"<article />"
        root = ElementTree.fromstring(xml_string)
        root_output = pub_history.add_pub_history(
            root, self.history_data, self.identifier
        )
        self.assertEqual(ElementTree.tostring(root_output), expected)


class TestAddPubHistoryMeca(unittest.TestCase):
    "tests for add_pub_history_meca()"

    def setUp(self):
        v1_events = (
            "<event>"
            "<event-desc>Preprint posted</event-desc>"
            '<date date-type="preprint" iso-8601-date="2024-04-27">'
            "<day>27</day>"
            "<month>04</month>"
            "<year>2024</year>"
            "</date>"
            '<self-uri content-type="preprint"'
            ' xlink:href="https://doi.org/10.1101/2024.04.25.591185" />'
            "</event>"
            "<event>"
            "<event-desc>Reviewed preprint v1</event-desc>"
            '<date date-type="reviewed-preprint" iso-8601-date="2024-07-17">'
            "<day>17</day>"
            "<month>07</month>"
            "<year>2024</year>"
            "</date>"
            '<self-uri content-type="reviewed-preprint"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1" />'
            '<self-uri content-type="editor-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa4">'
            "eLife assessment"
            "</self-uri>"
            '<self-uri content-type="referee-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa3">'
            "Reviewer #1 (Public Review):"
            "</self-uri>"
            '<self-uri content-type="referee-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa2">'
            "Reviewer #2 (Public Review):"
            "</self-uri>"
            '<self-uri content-type="referee-report"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa1">'
            "Reviewer #3 (Public Review):"
            "</self-uri>"
            '<self-uri content-type="author-comment"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.1.sa0">'
            "Author response:"
            "</self-uri>"
            "</event>"
        )
        v2_events = (
            "<event>"
            "<event-desc>Reviewed preprint v2</event-desc>"
            '<date date-type="reviewed-preprint" iso-8601-date="2024-07-18">'
            "<day>18</day>"
            "<month>07</month>"
            "<year>2024</year>"
            "</date>"
            '<self-uri content-type="reviewed-preprint"'
            ' xlink:href="https://doi.org/10.7554/eLife.99854.2" />'
            "</event>"
        )
        self.expected_v1_pub_history = (
            "<pub-history>" "%s" "</pub-history>"
        ) % v1_events
        self.expected_v2_pub_history = ("<pub-history>" "%s" "%s" "</pub-history>") % (
            v1_events,
            v2_events,
        )

    @patch("docmaptools.parse.get_web_content")
    def test_add_pub_history_meca(self, fake_get):
        fake_get.side_effect = mock_get_web_content
        root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<history />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        docmap_string = read_fixture("99854.json", mode="r")
        identifier = "10.7554/eLife.99854.2"
        expected = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>"
            "<history />"
            "%s"
            "</article-meta>"
            "</front>"
            "</article>"
        ) % self.expected_v1_pub_history
        # invoke
        result = pub_history.add_pub_history_meca(
            root, HISTORY_DATA_99854[0:2], docmap_string, identifier
        )
        # assert
        xml_string = ElementTree.tostring(result).decode("utf-8")
        self.assertEqual(xml_string, expected)

    @patch("docmaptools.parse.get_web_content")
    def test_insert_near_elocation_id(self, fake_get):
        "test for inserting pub-history near the elocation-id tag and no history tag"
        fake_get.side_effect = mock_get_web_content
        root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<elocation-id />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        docmap_string = read_fixture("99854.json", mode="r")
        identifier = "10.7554/eLife.99854.2"
        expected = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>"
            "<elocation-id />"
            "%s"
            "</article-meta>"
            "</front>"
            "</article>"
        ) % self.expected_v1_pub_history
        # invoke
        result = pub_history.add_pub_history_meca(
            root, HISTORY_DATA_99854[0:2], docmap_string, identifier
        )
        # assert
        xml_string = ElementTree.tostring(result).decode("utf-8")
        self.assertEqual(xml_string, expected)

    @patch("docmaptools.parse.get_web_content")
    def test_multiple_history_events(self, fake_get):
        "test more than one version DOI in history data"
        fake_get.side_effect = mock_get_web_content
        root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<elocation-id />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        docmap_string = read_fixture("99854.json", mode="r")
        identifier = "10.7554/eLife.99854.3"
        expected = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front>"
            "<article-meta>"
            "<elocation-id />"
            "%s"
            "</article-meta>"
            "</front>"
            "</article>"
        ) % self.expected_v2_pub_history
        # invoke
        result = pub_history.add_pub_history_meca(
            root, HISTORY_DATA_99854, docmap_string, identifier
        )
        # assert
        xml_string = ElementTree.tostring(result).decode("utf-8")
        self.assertEqual(xml_string, expected)

        # self.assertTrue(False)

    def test_no_article_meta(self):
        "test if XML has no article-meta tag"
        xml_string = b"<article />"
        root = ElementTree.fromstring(xml_string)
        history_data = [{"type": "preprint"}]
        docmap_string = {}
        identifier = "10.7554/eLife.95901.1"
        # invoke
        result = pub_history.add_pub_history_meca(
            root, history_data, docmap_string, identifier
        )
        # assert
        self.assertEqual(ElementTree.tostring(result), xml_string)

    def test_no_history_data(self):
        "test if history_data argument is empty"
        xml_string = b"<article />"
        root = ElementTree.fromstring(xml_string)
        history_data = []
        docmap_string = {}
        identifier = "10.7554/eLife.95901.1"
        # invoke
        result = pub_history.add_pub_history_meca(
            root, history_data, docmap_string, identifier
        )
        # assert
        self.assertEqual(ElementTree.tostring(result), xml_string)
