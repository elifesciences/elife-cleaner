import re
from xml.etree import ElementTree
from xml.etree.ElementTree import SubElement
import yaml
from elifecleaner import LOGGER


ASSESSMENT_TERMS_YAML = "assessment_terms.yaml"


def load_yaml(file_path=None):
    # load config from the file_path YAML file
    if not file_path:
        file_path = ASSESSMENT_TERMS_YAML
    try:
        with open(file_path, "r") as open_file:
            return yaml.load(open_file.read(), Loader=yaml.FullLoader)
    except:
        LOGGER.exception(
            "Exception in load_yaml for file_path: %s",
            file_path,
        )
        return None


def terms_data_from_yaml(file_path=None):
    return load_yaml(file_path)


def terms_data_by_terms(terms):
    "return a list of terms data which match the terms"
    terms_data = terms_data_from_yaml()
    if not terms_data:
        return {}
    # case-insensitive term matching using set operations to return a dict of matched YAML terms
    # if any of the supplied terms are found in the list of terms in the YAML then it is a hit
    return {
        term: data
        for term, data in terms_data.items()
        if set([term.lower() for term in terms]).intersection(
            set([term.lower() for term in data.get("terms", [])])
        )
    }


def terms_from_yaml():
    "get a list of unique terms from the YAML file"
    terms_data = terms_data_from_yaml()
    if not terms_data:
        return []
    terms_list = []
    for data in terms_data.values():
        terms_list += data.get("terms", [])
    return sorted(list(set(terms_list)))


def add_assessment_terms(root):
    "wrap specific terms with a bold tag in the body and add kwd tags"
    body_tag = root.find(".//body")
    if body_tag is not None:
        # list of terms from the YAML file
        terms = terms_from_yaml()

        # find matched terms for adding kwd tags later on
        matched_terms = []
        xml_string = ElementTree.tostring(body_tag, encoding="utf-8")
        for term in terms:
            term_match_groups = term_matches(xml_string.decode("utf-8"), term)
            for matched_term in term_match_groups:
                matched_terms.append(matched_term)

        # wrap terms with bold tags
        for tag_index, child_tag in enumerate(body_tag.iterfind("*")):
            # convert the tag to a string
            xml_string = ElementTree.tostring(child_tag, encoding="utf-8")
            # wrap terms with bold tag
            xml_string = xml_string_term_bold(xml_string.decode("utf-8"), terms)
            # convert the XML string back to an element
            new_child_tag = ElementTree.fromstring(xml_string)
            # remove old tag
            body_tag.remove(child_tag)
            # insert the new tag
            body_tag.insert(tag_index, new_child_tag)

        # add kwd-group and kwd tags
        terms_data = terms_data_by_terms(matched_terms)

        if terms_data:
            front_stub_tag = root.find(".//front-stub")

            # tags will be added in the order listed in the YAML file
            group_to_kwd_group_tag_map = {}
            for key, data in terms_data.items():
                if data.get("group") in group_to_kwd_group_tag_map.keys():
                    # reuse the kwd-group tag
                    kwd_group_tag = group_to_kwd_group_tag_map.get(data.get("group"))
                else:
                    # create a new kwd-group tag
                    kwd_group_tag = SubElement(front_stub_tag, "kwd-group")
                    kwd_group_tag.set("kwd-group-type", data.get("group"))
                    group_to_kwd_group_tag_map[data.get("group")] = kwd_group_tag
                # add a kwd tag
                kwd_tag = SubElement(kwd_group_tag, "kwd")
                kwd_tag.text = key


def term_match_pattern(term_text):
    "regular expression to find mentions of a term"
    return r"[\s\W](%s)\W" % (term_text)


def term_matches(xml_string, term_text):
    "get list of terms in text that are not already preceeded by the bold tag"
    return re.findall(term_match_pattern(term_text), xml_string, flags=re.IGNORECASE)


def xml_string_term_bold(xml_string, terms):
    "wrap occurences of each term in the XML string with a <bold> tag"
    open_tag = "<bold>"
    close_tag = "</bold>"
    for term in terms:
        if not term:
            continue
        # look for term in the text but not preceeded by a bold open tag
        term_match_groups = term_matches(xml_string, term)
        for matched_term in term_match_groups:
            safe_match_pattern = r"(?<!%s)(%s)(\W)" % (open_tag, matched_term)
            replacement_pattern = r"%s\1%s\2" % (
                open_tag,
                close_tag,
            )
            xml_string = re.sub(
                safe_match_pattern,
                replacement_pattern,
                xml_string,
                count=1,
                flags=re.IGNORECASE,
            )

    return xml_string
