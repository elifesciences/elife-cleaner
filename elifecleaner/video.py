from collections import OrderedDict
import re
from elifecleaner.utils import pad_msid

JOURNAL = "elife"

STRING_TO_TERM_MAP = {
    "animation": "video",
    "video": "video",
    "appendix": "app",
    "figure": "fig",
    "video supplement": "video",
    "videos supplement": "video",
    "supplementary video": "video",
}

IGNORE_TERM = "audio"

# todo!!!
# - raise exception when ignore term is found, or when video term is not found, to distinguish between them
# - enhance regex to handle mixed numeric values like 6A


def video_file_list(files):
    'get a list of file tags from the XML with @file-type="video"'
    return [
        file_data
        for file_data in files
        if isinstance(file_data, dict) and file_data.get("file_type") == "video"
    ]


def collect_video_data(files):
    "from the list of files collect file name and metadata for videos"
    video_files = video_file_list(files)
    video_data = []
    for file_data in video_files:
        data = OrderedDict()
        data["upload_file_nm"] = file_data.get("upload_file_nm")
        for meta in file_data.get("custom_meta"):
            if meta.get("meta_name") == "Title":
                data["title"] = meta.get("meta_value")
                break
        if len(data.keys()) > 1:
            video_data.append(data)
    return video_data


def rename_video_data(video_data, article_id):
    "generate new video filename and id from the video data"
    generated_video_data = []
    for data in video_data:
        video_data_output = OrderedDict()
        video_data_output["upload_file_nm"] = data.get("upload_file_nm")
        video_data_output["video_id"] = video_id(data.get("title"))
        video_data_output["video_filename"] = video_filename(
            data.get("title"), data.get("upload_file_nm"), article_id
        )
        generated_video_data.append(video_data_output)
    return generated_video_data


def video_data_from_files(files, article_id):
    "from a list of files return video data to be used in renaming files and XML"
    video_data = collect_video_data(files)
    return rename_video_data(video_data, article_id)


def all_terms(titles):
    "get a list of all terms for the title values"
    term_map = OrderedDict()
    for title in titles:
        term_map[title] = terms_from_title(title)
    # todo!! check all title values are non-None

    # check for duplicates
    a_list = [str(term) for term in term_map.values()]
    unique_terms = list({str(term) for term in term_map.values()})
    if len(a_list) != len(unique_terms):
        # todo!! handle duplicates
        return None
    return term_map


def terms_from_title(title):
    "from a title string extract video terms and numbers"
    terms = []
    # ignore the value if audio is in the title
    if IGNORE_TERM in title.lower():
        return []
    # convert underscore to space for more lenient matching
    title = title.replace("_", "")
    match_pattern = re.compile(r"(\D*?)(\d+)")
    for match in match_pattern.findall(title):
        section_term = match[0].lstrip(" -").strip().lower()
        if section_term in STRING_TO_TERM_MAP:
            term = OrderedDict()
            term["name"] = STRING_TO_TERM_MAP.get(section_term)
            term["number"] = match[1]
            terms.append(term)
    # check video is one of the name values
    if "video" in [term.get("name", "") for term in terms]:
        return terms
    return []


def video_id(title):
    "generate an id attribute for a video from its title string"
    id_string = ""
    terms = terms_from_title(title)
    if not terms:
        return None
    for term in terms:
        id_string += "%s%s" % (term.get("name"), term.get("number"))
    return id_string


def video_filename(title, upload_file_nm, article_id, journal=JOURNAL):
    "generate a new file name for a video file"
    terms = terms_from_title(title)
    if not terms:
        return None
    new_filename_parts = []
    new_filename_parts.append(journal)
    new_filename_parts.append(pad_msid(article_id))
    for term in terms:
        new_filename_parts.append("%s%s" % (term.get("name"), term.get("number")))
    new_filename = "-".join(new_filename_parts)
    # add file extension
    file_extension = upload_file_nm.split(".")[-1]
    new_filename = "%s.%s" % (new_filename, file_extension)
    return new_filename
