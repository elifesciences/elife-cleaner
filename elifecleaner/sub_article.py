from xml.etree.ElementTree import Element, SubElement
from jatsgenerator import build

XML_NAMESPACES = {
    "ali": "http://www.niso.org/schemas/ali/1.0/",
    "mml": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
}


def generate(sub_article_data, root_tag="article"):
    "generate a sub-article XML tag for each article"
    root = Element(root_tag)

    for data in sub_article_data:
        article = data.get("article")
        sub_article_root = data.get("xml_root")

        # set the article-type for each article
        sub_article_tag = sub_article(root, article.id, article.article_type)

        # front-stub parent tag
        front_stub_tag = SubElement(sub_article_tag, "front-stub")

        build.set_article_id(front_stub_tag, article)
        build.set_title_group(front_stub_tag, article)

        # add contributor tags
        if article.contributors:
            set_contrib(front_stub_tag, article)

        build.set_related_object(front_stub_tag, article)

        # set body from the sub-article XML
        body_tag = sub_article_root.find("body")
        if body_tag is not None:
            sub_article_tag.append(body_tag)

    # repair namespaces
    repair_namespaces(root)

    return root


def repair_namespaces(root):
    "repair XML namespaces by adding namespaces if missing"
    all_attributes = set()
    for tag in root.iter("*"):
        all_attributes = all_attributes.union(
            all_attributes, {attribute_name for attribute_name in tag.attrib.keys()}
        )
    prefix_attributes = {
        attrib.split(":")[0] for attrib in all_attributes if ":" in attrib
    }

    for prefix in prefix_attributes:
        if prefix in XML_NAMESPACES.keys():
            ns_attrib = "xmlns:%s" % prefix
            root.set(ns_attrib, XML_NAMESPACES.get(prefix))


def sub_article(parent, id_attribute=None, article_type=None):
    sub_article_tag = SubElement(parent, "sub-article")
    if id_attribute:
        sub_article_tag.set("id", id_attribute)
    if article_type:
        sub_article_tag.set("article-type", article_type)
    return sub_article_tag


def set_contrib(parent, article, contrib_type=None):
    contrib_group = SubElement(parent, "contrib-group")

    for contributor in article.contributors:
        contrib_tag = SubElement(contrib_group, "contrib")
        contrib_tag.set("contrib-type", contributor.contrib_type)
        build.set_contrib_name(contrib_tag, contributor)

        # set role tag
        build.set_contrib_role(contrib_tag, contrib_type, contributor)

        # set orcid tag with authenticated=true tag attribute
        build.set_contrib_orcid(contrib_tag, contributor)

        # add aff tag(s)
        for affiliation in contributor.affiliations:
            build.set_aff(
                contrib_tag,
                affiliation,
                contrib_type,
                aff_id=None,
                tail="",
                institution_wrap=True,
            )
