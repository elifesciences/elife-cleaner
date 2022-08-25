from collections import Counter, OrderedDict
import re
from elifecleaner import LOGGER
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
    video_terms = all_terms_map(video_data)
    for data in video_data:
        video_data_output = OrderedDict()
        terms = video_terms.get(data.get("upload_file_nm"))
        video_data_output["upload_file_nm"] = data.get("upload_file_nm")
        video_data_output["video_id"] = video_id_from_terms(terms)
        video_data_output["video_filename"] = video_filename_from_terms(
            terms, data.get("upload_file_nm"), article_id
        )
        generated_video_data.append(video_data_output)
    return generated_video_data


def video_data_from_files(files, article_id):
    "from a list of files return video data to be used in renaming files and XML"
    video_data = collect_video_data(files)
    return rename_video_data(video_data, article_id)


def all_terms_map(video_data):
    "get a map file name to oterms for all videos"
    term_map = OrderedDict()
    for data in video_data:
        term_map[data.get("upload_file_nm")] = terms_from_title(data.get("title"))
    # todo!! check all title values are non-None

    # check for duplicates
    a_list = [str(term) for term in term_map.values()]
    unique_terms = list({str(term) for term in term_map.values()})
    if len(a_list) != len(unique_terms):
        # handle duplicates
        LOGGER.info("found duplicate video term values")
        # renumber duplicate terms
        term_map = renumber(term_map)

    return term_map


def renumber(term_map):
    "renumber duplicate video terms in the map"
    # detect duplicate video_id strings and collect the keys of the duplicates
    # first generate a map of video file name to video_id values
    key_map = {key: video_id_from_terms(value) for (key, value) in term_map.items()}
    # get a list of duplicates
    duplicate_video_id_counter = Counter([video_id for video_id in key_map.values()])
    duplicates = [key for key, value in duplicate_video_id_counter.items() if value > 1]
    LOGGER.info("duplicate values: %s", duplicates)
    # for each of the duplicates, find all the keys with the same string prefix
    prefix_to_keys_map = {}
    for dupe in duplicates:
        video_id_prefix = dupe.rstrip("1234567890")
        prefix_to_keys_map[video_id_prefix] = [
            key for key, value in key_map.items() if value.startswith(video_id_prefix)
        ]
    # renumber the videos with duplicate numbers
    return renumber_term_map(term_map, prefix_to_keys_map)


def renumber_term_map(term_map, prefix_to_keys_map):
    "replace duplicate number values in the term_map for each having the same prefix"
    for prefix, keys in prefix_to_keys_map.items():
        key_map = {
            key: int(terms[-1].get("number"))
            for key, terms in term_map.items()
            if key in keys
        }
        # assign new number to duplicate number values
        new_key_map = renumber_key_map(prefix, key_map)
        # replace the number values with new ones
        for key, new_number in new_key_map.items():
            old_number = term_map[key][-1].get("number")
            if str(new_number) != old_number:
                LOGGER.info(
                    "replacing number %s with %s for term %s",
                    old_number,
                    new_number,
                    key,
                )
            term_map[key][-1]["number"] = str(new_number)
    return term_map


def renumber_key_map(prefix, key_map):
    "replace duplicate numbers in the video key_map with new numbers"
    all_numbers = [number for key, number in key_map.items()]
    LOGGER.info("number values used for video prefix %s: %s", prefix, all_numbers)
    duplicate_number_counter = Counter(all_numbers)
    duplicate_numbers = [
        key for key, value in duplicate_number_counter.items() if value > 1
    ]
    LOGGER.info(
        "duplicate number values for video prefix %s: %s", prefix, duplicate_numbers
    )
    # list of replacement numbers are those not already in the list starting from 1
    replacement_numbers = [
        number
        for number in range(min(all_numbers), len(all_numbers) + min(all_numbers))
        if number not in all_numbers
    ]
    LOGGER.info(
        "replacement number values can be used for video prefix %s: %s",
        prefix,
        replacement_numbers,
    )
    replacement_index = 0
    numbers_used = []
    for key in key_map.keys():
        number = key_map[key]
        # replace the number if it is a known duplicate and it has already been used at least once
        if int(number) in duplicate_numbers:
            if number in numbers_used:
                new_number = replacement_numbers[replacement_index]
                key_map[key] = new_number
                numbers_used.append(new_number)
                replacement_index += 1
            else:
                numbers_used.append(number)
    return key_map


def terms_from_title(title):
    "from a title string extract video terms and numbers"
    terms = []
    # ignore the value if audio is in the title
    if IGNORE_TERM in title.lower():
        return []
    # convert some punctuation to space for more lenient matching
    for char in ["_", "-"]:
        title = title.replace(char, " ")
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
    terms = terms_from_title(title)
    return video_id_from_terms(terms)


def video_id_from_terms(terms):
    id_string = ""
    if not terms:
        return None
    for term in terms:
        id_string += "%s%s" % (term.get("name"), term.get("number"))
    return id_string


def video_filename(title, upload_file_nm, article_id, journal=JOURNAL):
    "generate a new file name for a video file"
    terms = terms_from_title(title)
    return video_filename_from_terms(terms, upload_file_nm, article_id, journal)


def video_filename_from_terms(terms, upload_file_nm, article_id, journal=JOURNAL):
    "generate a new file name for a video file using the terms provided"
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
