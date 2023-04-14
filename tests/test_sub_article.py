import os
import unittest
import zipfile
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from xml.dom import minidom
from mock import patch
from elifearticle.article import (
    Affiliation,
    Article,
    Contributor,
    RelatedArticle,
    Role,
)
from elifetools import xmlio
from elifecleaner import configure_logging, LOGGER, parse, sub_article
from tests.helpers import delete_files_in_folder, read_fixture, read_log_file_lines


ARTICLE_TITLES = [
    b"Evaluation Summary: <italic>test</italic>",
    b"Reviewer #1 (Public Review):",
    b"Author Response:",
    b"Consensus Public Review:",
]

CONTENT_JSON = [
    {
        "type": "evaluation-summary",
        "html": b"<p><strong>%s</strong></p><p>Test evaluation summary.</p>"
        % ARTICLE_TITLES[0],
    },
    {
        "type": "review-article",
        "html": b"<p><strong>%s</strong></p><p>Test review article.</p>"
        % ARTICLE_TITLES[1],
    },
    {
        "type": "reply",
        "html": b"<p><strong>%s</strong></p><p>Test reply.</p>" % ARTICLE_TITLES[2],
    },
    {
        "type": "review-article",
        "html": b"<p><strong>%s</strong></p><p>Test consensus review article.</p>"
        % ARTICLE_TITLES[3],
    },
]


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


def editor_report_article_fixture(
    id_attribute="sa0",
    doi="10.7554/eLife.1234567890.4.sa0",
):
    "populate an editor-report Article for testing"
    article = Article(doi)
    article.article_type = "editor-report"
    article.title = "eLife assessment"
    article.id = id_attribute
    related_article = RelatedArticle()
    related_article.ext_link_type = "continued-by"
    related_article.xlink_href = (
        "https://sciety.org/articles/activity/10.1101/2021.11.09.467796"
    )
    article.related_articles = [related_article]
    # contributors
    author = Contributor("author", "Surname", "Given")
    author.suffix = "X"
    author.orcid = "https://orcid.org/0000-0000-0000-0000"
    author.orcid_authenticated = True
    # aff
    aff = Affiliation()
    aff.phone = "Phone"
    aff.fax = "Fax"
    aff.department = "Department"
    aff.institution = "Institution"
    aff.city = "City"
    aff.country = "Country"
    aff.ror = "ror"
    author.set_affiliation(aff)
    # add the author to the article
    article.add_contributor(author)
    return article


def referee_report_article_fixture(
    id_attribute="sa2",
    doi="10.7554/eLife.1234567890.4.sa2",
    title="Reviewer #1 (public review)",
):
    "populate a referee-report Article for testing"
    article = Article(doi)
    article.article_type = "referee-report"
    article.title = title
    article.id = id_attribute
    # contributors
    anonymous_author = Contributor("author", None, None)
    anonymous_author.roles = [Role("Reviewer", "referee")]
    # setattr(anonymous_author, "anonymous", True)
    anonymous_author.anonymous = True
    # add the author to the article
    article.add_contributor(anonymous_author)
    return article


def author_comment_article_fixture(
    id_attribute="sa3",
    doi="10.7554/eLife.1234567890.4.sa3",
):
    "populate an author-comment Article for testing"
    article = Article(doi)
    article.article_type = "author-comment"
    article.title = "Author response"
    article.id = id_attribute
    # contributors
    author = Contributor("author", "Surname", "Given")
    author.suffix = "X"
    article.add_contributor(author)
    return article


def xml_content(article_title):
    "return an XML content fixture with the article_title"
    return (
        b"<root><front-stub><title-group><article-title>%s"
        b"</article-title></title-group>\n</front-stub>"
        b"<body><p>The ....</p>\n</body>"
        b"</root>"
    ) % article_title


class TestReorderReviewArticles(unittest.TestCase):
    def test_reorder_review_articles(self):
        content_list = [
            {"xml": b"No match"},
            {"xml": xml_content(b"Reviewer #15 (Public Review):")},
            {"xml": xml_content(b"Reviewer #2 (Public Review):")},
            {"xml": xml_content(b"Reviewer #2 (Public Review):")},
            {"xml": xml_content(b"Reviewer #1 (Public Review):")},
            {"xml": xml_content(b"Reviewer #3 (Public Review):")},
        ]
        result = sub_article.reorder_review_articles(content_list)
        # assertions of the new sort order
        self.assertEqual(result[0], content_list[0])
        self.assertEqual(result[1], content_list[4])
        self.assertEqual(result[2], content_list[2])
        self.assertEqual(result[3], content_list[3])
        self.assertEqual(result[4], content_list[5])
        self.assertEqual(result[5], content_list[1])


class TestReorderContentJson(unittest.TestCase):
    def test_reorder_content_json(self):
        content_json = [
            {
                "type": "review-article",
                "xml": xml_content(b"Reviewer #2 (Public Review):"),
            },
            {"type": "reply", "xml": xml_content(b"Author Response:")},
            {"type": "evaluation-summary", "xml": xml_content(b"Evaluation Summary:")},
            {
                "type": "review-article",
                "xml": xml_content(b"Reviewer #1 (Public Review):"),
            },
        ]
        # type values in the expected order
        expected_types = [
            "evaluation-summary",
            "review-article",
            "review-article",
            "reply",
        ]
        result = sub_article.reorder_content_json(content_json)
        self.assertEqual([content.get("type") for content in result], expected_types)
        # assert the sorting by article-title was successful
        self.assertTrue(b"Reviewer #1" in result[1].get("xml"))


class TestAddSubArticleXml(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        self.log_handler = configure_logging(self.log_file)
        self.original_repair_xml_value = parse.REPAIR_XML

    def tearDown(self):
        LOGGER.removeHandler(self.log_handler)
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])
        parse.REPAIR_XML = self.original_repair_xml_value

    @patch("elifecleaner.sub_article.docmap_parse.populate_docmap_content")
    @patch("requests.get")
    def test_add_sub_article_xml(self, mock_get, mock_sub_article_data):
        mock_get.return_value = True
        mock_sub_article_data.return_value = CONTENT_JSON
        zip_file = "tests/test_data/08-11-2020-FA-eLife-64719.zip"
        xml_file_name = "08-11-2020-FA-eLife-64719/08-11-2020-FA-eLife-64719.xml"
        with zipfile.ZipFile(zip_file, "r") as input_zipfile:
            input_zipfile.extract(xml_file_name, self.temp_dir)
        docmap_string = read_fixture("2021.06.02.446694.docmap.json", mode="r")
        article_xml = os.path.join(self.temp_dir, xml_file_name)
        result = sub_article.add_sub_article_xml(docmap_string, article_xml)
        self.assertEqual(len(result.findall(".//sub-article")), 4)
        # For now assert each log file message appears, this may need adjustment later
        expected_log_file_lines = [
            "INFO elifecleaner:sub_article:add_sub_article_xml: Parsing article XML into root Element\n",
            "INFO elifecleaner:sub_article:add_sub_article_xml: Parsing article XML into an Article object\n",
            "INFO elifecleaner:sub_article:add_sub_article_xml: Populate sub article data\n",
            "INFO elifecleaner:sub_article:sub_article_data: Parsing docmap json\n",
            "INFO elifecleaner:sub_article:sub_article_data: Collecting content_json\n",
            "INFO elifecleaner:sub_article:sub_article_data: Downloading HTML for each web-content URL\n",
            "INFO elifecleaner:sub_article:sub_article_data: Formatting content json into article and XML data\n",
            "INFO elifecleaner:sub_article:add_sub_article_xml: Generate sub-article XML\n",
            "INFO elifecleaner:sub_article:add_sub_article_xml: Appending sub-article tags to the XML root\n",
        ]
        log_file_lines = read_log_file_lines(self.log_file)
        for line in expected_log_file_lines:
            self.assertTrue(line in log_file_lines)


class TestSubArticleData(unittest.TestCase):
    @patch("requests.get")
    def test_sub_article_data(self, mock_get):
        article_title = b"Evaluation Summary: <italic>test</italic>"
        mock_get.return_value = FakeResponse(
            200, content=b"<p><strong>%s</strong></p><p>Test.</p>" % article_title
        )
        docmap_string = read_fixture("2021.06.02.446694.docmap.json", mode="r")
        article = Article("10.7554/eLife.79713.1")
        # invoke
        sub_article_data = sub_article.sub_article_data(docmap_string, article)
        # assertions
        self.assertEqual(len(sub_article_data), 5)
        self.assertEqual(sorted(sub_article_data[0].keys()), ["article", "xml_root"])
        self.assertTrue(isinstance(sub_article_data[0].get("article"), Article))
        self.assertTrue(isinstance(sub_article_data[0].get("xml_root"), Element))
        # assertions for Article objects
        self.assertEqual(
            sub_article_data[0].get("article").article_type, "editor-report"
        )
        self.assertEqual(sub_article_data[0].get("article").doi, "%s.sa0" % article.doi)
        self.assertEqual(
            sub_article_data[0].get("article").title, article_title.decode("utf8")
        )
        # assertions for XML root
        self.assertIsNotNone(
            sub_article_data[0].get("xml_root").find(".//article-title")
        )


class TestSubArticleId(unittest.TestCase):
    def test_sub_article_id(self):
        index = 0
        expected = "sa0"
        self.assertEqual(sub_article.sub_article_id(index), expected)


class TestSubArticleDoi(unittest.TestCase):
    def test_sub_article_doi(self):
        article_doi = "10.7554/eLife.79713.1"
        index = 0
        self.assertEqual(
            sub_article.sub_article_doi(article_doi, index),
            "%s.sa%s" % (article_doi, index),
        )


class TestSubArticleContributors(unittest.TestCase):
    def setUp(self):
        self.article_object = Article()
        author = Contributor("author", "Surname", "Given")
        author.suffix = "X"
        author.orcid = "https://orcid.org/0000-0000-0000-0000"
        author.orcid_authenticated = True
        self.article_object.contributors.append(author)
        editor = Contributor("editor", "Itor", "Ed")
        self.article_object.editors.append(editor)

    def test_editor_report(self):
        "test editor-report article type"
        sub_article_object = Article()
        sub_article_object.article_type = "editor-report"
        sub_article.sub_article_contributors(self.article_object, sub_article_object)
        self.assertEqual(len(sub_article_object.contributors), 1)
        self.assertEqual(sub_article_object.contributors[0].given_name, "Ed")

    def test_referee_report(self):
        "test referee-report article type"
        sub_article_object = Article()
        sub_article_object.article_type = "referee-report"
        sub_article.sub_article_contributors(self.article_object, sub_article_object)
        self.assertEqual(len(sub_article_object.contributors), 1)
        # is anonymous
        self.assertEqual(sub_article_object.contributors[0].anonymous, True)

    def test_author_comment(self):
        "test author-comment article type"
        sub_article_object = Article()
        sub_article_object.article_type = "author-comment"
        sub_article.sub_article_contributors(self.article_object, sub_article_object)
        self.assertEqual(len(sub_article_object.contributors), 1)
        self.assertEqual(sub_article_object.contributors[0].given_name, "Given")

    def test_unsupported(self):
        "test unsupported article type"
        sub_article_object = Article()
        sub_article_object.article_type = "unsupported"
        sub_article.sub_article_contributors(self.article_object, sub_article_object)
        # no authors
        self.assertEqual(len(sub_article_object.contributors), 0)


class TestBuildSubArticleObject(unittest.TestCase):
    def test_build_sub_article_object(self):
        "test review-article example"
        article_object = Article("10.7554/eLife.79713.1")
        xml_root = ElementTree.fromstring(
            b"<article><front-stub><title-group>"
            b"<article-title>Title</article-title>"
            b"</title-group></front-stub></article>"
        )
        content = {"type": "review-article"}
        index = 1
        sub_article_object = sub_article.build_sub_article_object(
            article_object, xml_root, content, index
        )
        self.assertEqual(sub_article_object.doi, "10.7554/eLife.79713.1.sa1")
        self.assertEqual(sub_article_object.title, "Title")
        self.assertEqual(len(sub_article_object.contributors), 1)

    def test_minimal(self):
        "test minimal, incomplete, arguments supplied"
        article_object = Article("10.7554/eLife.79713.1")
        xml_root = Element("root")
        content = {}
        index = 0
        sub_article_object = sub_article.build_sub_article_object(
            article_object, xml_root, content, index
        )
        self.assertEqual(sub_article_object.doi, "10.7554/eLife.79713.1.sa0")
        self.assertEqual(sub_article_object.title, None)
        self.assertEqual(len(sub_article_object.contributors), 0)


class TestFormatContentJson(unittest.TestCase):
    def test_format_content_json(self):
        article_titles = [
            b"Evaluation Summary: <italic>test</italic>",
            b"Reviewer #1 (Public Review):",
            b"Author Response:",
        ]
        article = Article("10.7554/eLife.79713.1")
        article.contributors = [Contributor("author", "Surname", "Given")]
        article.editors = [Contributor("editor", "Editor", "Given")]
        # invoke
        sub_article_data = sub_article.format_content_json(CONTENT_JSON, article)
        # assertions
        self.assertEqual(len(sub_article_data), 4)
        self.assertEqual(sorted(sub_article_data[0].keys()), ["article", "xml_root"])
        self.assertTrue(isinstance(sub_article_data[0].get("article"), Article))
        self.assertTrue(isinstance(sub_article_data[0].get("xml_root"), Element))
        # assertions for Article objects
        article_0 = sub_article_data[0].get("article")
        self.assertEqual(article_0.article_type, "editor-report")
        self.assertEqual(article_0.doi, "%s.sa0" % article.doi)
        self.assertEqual(article_0.title, article_titles[0].decode("utf8"))
        # article 0 contributors
        self.assertEqual(len(article_0.contributors), 1)
        # article 0 contrib 0
        self.assertEqual(
            article_0.contributors[0].roles[0].text,
            "Reviewing Editor",
        )
        self.assertEqual(
            article_0.contributors[0].roles[0].specific_use,
            "editor",
        )
        # article 1
        article_1 = sub_article_data[1].get("article")
        self.assertEqual(article_1.article_type, "referee-report")
        # article 1 contributors
        self.assertEqual(len(article_1.contributors), 1)
        # article 1 contrib 0
        self.assertEqual(article_1.contributors[0].roles[0].text, "Reviewer")
        self.assertEqual(
            article_1.contributors[0].roles[0].specific_use,
            "referee",
        )

        # article 2
        article_2 = sub_article_data[2].get("article")
        self.assertEqual(article_2.article_type, "referee-report")
        # article 2 contributors
        self.assertEqual(len(article_2.contributors), 1)
        # article 2 contrib 0
        self.assertEqual(article_2.contributors[0].roles[0].text, "Reviewer")
        self.assertEqual(
            article_2.contributors[0].roles[0].specific_use,
            "referee",
        )

        # article 3
        article_3 = sub_article_data[3].get("article")
        self.assertEqual(article_3.article_type, "author-comment")
        # article 3 contributors
        self.assertEqual(len(article_3.contributors), 1)
        # article 3 contrib 0
        self.assertEqual(article_3.contributors[0].roles[0].text, "Author")
        self.assertEqual(
            article_3.contributors[0].roles[0].specific_use,
            "author",
        )

        # assertions for XML root
        body_tag = sub_article_data[0].get("xml_root").find(".//body")
        self.assertIsNotNone(body_tag)
        self.assertEqual(body_tag.find("p").text, "Test evaluation summary.")


class TestGenerate(unittest.TestCase):
    def test_generate(self):
        editor_report_article = editor_report_article_fixture()
        referee_report_article = referee_report_article_fixture()
        author_comment_article = author_comment_article_fixture()

        # XML generated from docmap-tools
        # register XML namespaces
        xmlio.register_xmlns()
        editor_report_xml_string = (
            '<root xmlns:mml="http://www.w3.org/1998/Math/MathML">'
            "<body>"
            "<p><bold>Test</bold> <sup>superscript</sup> <sub>subscript</sub> &amp; p&lt;0.001 "
            "<italic>C. elegans</italic></p>"
            "<p><inline-formula>"
            '<mml:math display="inline" alttext="n"><mml:mi>n</mml:mi></mml:math>'
            "</inline-formula></p>"
            "</body></root>"
        )
        editor_report_sub_article_root = ElementTree.fromstring(
            editor_report_xml_string
        )
        referee_report_xml_string = "<root><body><p>Review.</p></body></root>"
        referee_report_sub_article_root = ElementTree.fromstring(
            referee_report_xml_string
        )
        author_comment_xml_string = (
            "<root>"
            "<body>"
            '<disp-quote content-type="editor-comment">Quotation.</disp-quote>'
            "<p>Response.</p>"
            "</body>"
            "</root>"
        )
        author_comment_sub_article_root = ElementTree.fromstring(
            author_comment_xml_string
        )

        # assemble sub article data
        sub_article_1 = {
            "article": editor_report_article,
            "xml_root": editor_report_sub_article_root,
        }
        sub_article_2 = {
            "article": referee_report_article,
            "xml_root": referee_report_sub_article_root,
        }
        sub_article_3 = {
            "article": author_comment_article,
            "xml_root": author_comment_sub_article_root,
        }
        # build XML
        sub_article_data = [sub_article_1, sub_article_2, sub_article_3]
        root = sub_article.generate(sub_article_data)
        expected = read_fixture("sub_articles.xml", mode="rb")

        rough_xml_string = ElementTree.tostring(root, "utf-8")
        # parse the XML string to produce pretty output and
        # also check for XML namespace parsing errors
        reparsed = minidom.parseString(rough_xml_string)
        pretty_xml_string = reparsed.toprettyxml(indent="  ", encoding="utf-8")

        self.assertEqual(pretty_xml_string, expected)

    def test_editor_report(self):
        "test editor-report example with specific terms in the abstract"
        editor_report_article = Article("10.7554/eLife.79713.1")
        editor_report_article.article_type = "editor-report"
        editor_report_article.title = "eLife assessment"
        editor_report_xml_string = (
            "<root>"
            "<body>"
            "<p><strong>eLife assessment</strong></p>"
            "<p>Landmark convincing evaluation, "
            "convincingly compelling if "
            "incompletely.</p>"
            "<p>And important.</p>"
            "</body></root>"
        )
        editor_report_sub_article_root = ElementTree.fromstring(
            editor_report_xml_string
        )
        # assemble sub article data
        sub_article_1 = {
            "article": editor_report_article,
            "xml_root": editor_report_sub_article_root,
        }

        root = sub_article.generate([sub_article_1])
        expected = (
            b'<article><sub-article article-type="editor-report">'
            b"<front-stub>"
            b'<article-id pub-id-type="doi">10.7554/eLife.79713.1</article-id>'
            b"<title-group><article-title>eLife assessment</article-title></title-group>"
            b'<kwd-group kwd-group-type="evidence-strength">'
            b"<kwd>Compelling</kwd>"
            b"<kwd>Convincing</kwd>"
            b"<kwd>Incomplete</kwd>"
            b"</kwd-group>"
            b'<kwd-group kwd-group-type="claim-importance">'
            b"<kwd>Important</kwd>"
            b"<kwd>Landmark</kwd>"
            b"</kwd-group>"
            b"</front-stub>"
            b"<body>"
            b"<p><strong>eLife assessment</strong></p>"
            b"<p><bold>Landmark</bold> <bold>convincing</bold> evaluation, "
            b"<bold>convincingly</bold> <bold>compelling</bold> if "
            b"<bold>incompletely</bold>.</p>"
            b"<p>And <bold>important</bold>.</p>"
            b"</body>"
            b"</sub-article>"
            b"</article>"
        )
        rough_xml_string = ElementTree.tostring(root, "utf-8")
        self.assertEqual(rough_xml_string, expected)
