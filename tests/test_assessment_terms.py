import unittest
from xml.etree import ElementTree
from mock import patch
import yaml
from elifetools import xmlio
from elifecleaner import assessment_terms


class TestLoadYaml(unittest.TestCase):
    def test_load_yaml(self):
        "load YAML file using the default"
        result = assessment_terms.load_yaml()
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))

    def test_no_file(self):
        "test if no file is supplied also uses the default"
        result = assessment_terms.load_yaml(None)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))

    @patch.object(yaml, "load")
    def test_exception(self, mock_load):
        "test an exception when loading the YAML file"
        mock_load.side_effect = Exception("An exception")
        result = assessment_terms.load_yaml()
        self.assertEqual(result, None)


class TestTermsDataByTerms(unittest.TestCase):
    def setUp(self):
        self.terms_data = {
            "Beagle": {"group": "dog", "terms": ["beagle", "beagles"]},
            "Dingo": {"group": "dog", "terms": ["dingo", "dingos"]},
            "Dodo": {"group": "bird", "terms": ["dodo", "dodos"]},
            "Parrot": {"group": "bird", "terms": ["parrot", "parrots"]},
        }

    @patch.object(assessment_terms, "terms_data_from_yaml")
    def test_terms_data_by_terms(self, mock_terms_data):
        mock_terms_data.return_value = self.terms_data
        terms = ["dodo", "dodos", "DINGO"]
        expected_keys = ["Dingo", "Dodo"]
        result = assessment_terms.terms_data_by_terms(terms)
        self.assertEqual(sorted(result.keys()), sorted(expected_keys))

    @patch.object(assessment_terms, "terms_data_from_yaml")
    def test_no_match(self, mock_terms_data):
        mock_terms_data.return_value = self.terms_data
        terms = ["penguin"]
        expected_keys = []
        result = assessment_terms.terms_data_by_terms(terms)
        self.assertEqual(sorted(result.keys()), sorted(expected_keys))

    @patch.object(assessment_terms, "terms_data_from_yaml")
    def test_no_data(self, mock_terms_data):
        mock_terms_data.return_value = None
        terms = ["penguin"]
        expected_keys = []
        result = assessment_terms.terms_data_by_terms(terms)
        self.assertEqual(sorted(result.keys()), sorted(expected_keys))

    @patch.object(assessment_terms, "terms_data_from_yaml")
    def test_none(self, mock_terms_data):
        mock_terms_data.return_value = None
        terms = ["dodo"]
        expected_keys = []
        result = assessment_terms.terms_data_by_terms(terms)
        self.assertEqual(sorted(result.keys()), sorted(expected_keys))


class TestTermsFromYaml(unittest.TestCase):
    def test_terms_from_yaml(self):
        self.assertTrue(len(assessment_terms.terms_from_yaml()) > 0)

    @patch.object(assessment_terms, "terms_data_from_yaml")
    def test_yaml_none(self, mock_terms_data):
        mock_terms_data.return_value = None
        self.assertEqual(assessment_terms.terms_from_yaml(), [])


class TestAddAssessmentTerms(unittest.TestCase):
    def setUp(self):
        # register XML namespaces
        xmlio.register_xmlns()

    def test_add_assessment_terms(self):
        "test editor-report example with specific terms in the abstract"
        xml_root = ElementTree.fromstring(
            b'<article xmlns:xlink="http://www.w3.org/1999/xlink"><front-stub><title-group>'
            b"<article-title>eLife assessment</article-title>"
            b"</title-group></front-stub>"
            b"<body>"
            b"<p>Landmark convincing evaluation "
            b'(<ext-link xlink:href="https://example.org"/>), '
            b"convincingly compelling if "
            b"incompletely unconvincing (convincingly).</p>"
            b"</body>"
            b"</article>"
        )

        expected_xml = (
            b'<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<front-stub>"
            b"<title-group>"
            b"<article-title>eLife assessment</article-title>"
            b"</title-group>"
            b'<kwd-group kwd-group-type="evidence-strength">'
            b"<kwd>Compelling</kwd>"
            b"<kwd>Convincing</kwd>"
            b"<kwd>Incomplete</kwd>"
            b"</kwd-group>"
            b'<kwd-group kwd-group-type="claim-importance">'
            b"<kwd>Landmark</kwd>"
            b"</kwd-group>"
            b"</front-stub>"
            b"<body><p><bold>Landmark</bold> <bold>convincing</bold> evaluation "
            b'(<ext-link xlink:href="https://example.org" />), '
            b"<bold>convincingly</bold> <bold>compelling</bold> if "
            b"<bold>incompletely</bold> unconvincing (<bold>convincingly</bold>).</p>"
            b"</body>"
            b"</article>"
        )

        assessment_terms.add_assessment_terms(xml_root)
        rough_xml_string = ElementTree.tostring(xml_root, "utf-8")
        # assert
        self.assertEqual(rough_xml_string, expected_xml)

    def test_multiple_p_tags(self):
        "test editor-report with multiple p tags in the abstract"
        xml_root = ElementTree.fromstring(
            b"<sub-article><front-stub><title-group>"
            b"<article-title>eLife assessment</article-title>"
            b"</title-group></front-stub>"
            b"<body>"
            b"<p>Landmark.</p>"
            b"<p><bold>Important</bold>!</p>"
            b"</body>"
            b"</sub-article>"
        )

        expected_xml = (
            b"<sub-article>"
            b"<front-stub>"
            b"<title-group><article-title>eLife assessment</article-title></title-group>"
            b'<kwd-group kwd-group-type="claim-importance">'
            b"<kwd>Important</kwd>"
            b"<kwd>Landmark</kwd>"
            b"</kwd-group>"
            b"</front-stub>"
            b"<body>"
            b"<p><bold>Landmark</bold>.</p>"
            b"<p><bold>Important</bold>!</p>"
            b"</body>"
            b"</sub-article>"
        )

        assessment_terms.add_assessment_terms(xml_root)
        rough_xml_string = ElementTree.tostring(xml_root, "utf-8")
        # assert
        self.assertEqual(rough_xml_string, expected_xml)

    def test_non_p_tag(self):
        "test for a tag which is not a p tag"
        xml_string = (
            b"<article>"
            b"<front-stub>"
            b"<title-group>"
            b"<article-title>eLife assessment</article-title>"
            b"</title-group>"
            b"</front-stub>"
            b"<body>"
            b"<sec>Landmark</sec>"
            b"</body>"
            b"</article>"
        )
        expected_xml = (
            b"<article>"
            b"<front-stub>"
            b"<title-group>"
            b"<article-title>eLife assessment</article-title>"
            b"</title-group>"
            b'<kwd-group kwd-group-type="claim-importance">'
            b"<kwd>Landmark</kwd>"
            b"</kwd-group>"
            b"</front-stub>"
            b"<body><sec><bold>Landmark</bold></sec></body>"
            b"</article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        assessment_terms.add_assessment_terms(xml_root)
        rough_xml_string = ElementTree.tostring(xml_root, "utf-8")
        self.assertEqual(rough_xml_string, expected_xml)


class TestXmlStringTermBold(unittest.TestCase):
    def test_xml_string_term_bold(self):
        test_data = {
            "xml_string": ("<p>In Author Response image 1, yes response.</p>"),
            "terms": ["response"],
            "expected": (
                "<p>In "
                "Author <bold>Response</bold> image 1, yes <bold>response</bold>.</p>"
            ),
        }
        modified_xml_string = assessment_terms.xml_string_term_bold(
            test_data.get("xml_string"), test_data.get("terms")
        )
        self.assertEqual(modified_xml_string, test_data.get("expected"))

    def test_blank_terms(self):
        "test for blank or missing terms"
        test_data = {
            "xml_string": ("<p>In Author Response image 1, yes response.</p>"),
            "terms": ["", None],
            "expected": ("<p>In " "Author Response image 1, yes response.</p>"),
        }
        modified_xml_string = assessment_terms.xml_string_term_bold(
            test_data.get("xml_string"), test_data.get("terms")
        )
        self.assertEqual(modified_xml_string, test_data.get("expected"))
