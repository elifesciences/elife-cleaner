import unittest
from xml.etree import ElementTree
from xml.dom import minidom
from elifearticle.article import (
    Affiliation,
    Article,
    Contributor,
    RelatedArticle,
    Role,
)
from elifetools import xmlio
from elifecleaner import sub_article
from tests.helpers import read_fixture


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
