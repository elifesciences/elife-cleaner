import os
import unittest
from collections import OrderedDict
from elifecleaner import configure_logging, video
from tests.helpers import delete_files_in_folder, read_log_file_lines


VIDEO_TITLE_EXAMPLES = [
    {
        "comment": "Example of Animation",
        "article_id": 63107,
        "title": "Animation 1",
        "upload_file_nm": "Animation 1.gif",
        "id": "video1",
        "filename": "elife-63107-video1.gif",
    },
    {
        "comment": "Example of Appendix",
        "article_id": 64000,
        "title": "Appendix 12-figure 1-video 1",
        "upload_file_nm": "Appendix 12 Figure A1video 1.mov",
        "id": "app12fig1video1",
        "filename": "elife-64000-app12-fig1-video1.mov",
    },
    {
        "comment": "Example including Audio will be ignored",
        "article_id": 62329,
        "title": "Audio 1",
        "upload_file_nm": "MaleNarrator_unaltered.mp4",
        "id": None,
        "filename": None,
    },
    {
        "comment": "Example of figure animation",
        "article_id": 56603,
        "title": "Figure 2-animation 1",
        "upload_file_nm": "violindecoding_movie.gif",
        "id": "fig2video1",
        "filename": "elife-56603-fig2-video1.gif",
    },
    {
        "comment": "Example of video supplement",
        "article_id": 41328,
        "title": "Figure 1-video supplement 1",
        "upload_file_nm": "task low noise.avi",
        "id": "fig1video1",
        "filename": "elife-41328-fig1-video1.avi",
    },
    {
        "comment": "Example of videos supplement, plural",
        "article_id": 52986,
        "title": "Figure 1-Videos Supplement 1",
        "upload_file_nm": "Figure 1 Video Supplemental 1A.mp4",
        "id": "fig1video1",
        "filename": "elife-52986-fig1-video1.mp4",
    },
    {
        "comment": "Example of Figure Supplement",
        "article_id": 58962,
        "title": "Figure 1 - Figure Supplement 3 - video 2",
        "upload_file_nm": (
            "Figure 1 Figure supplement 3 video 2. wildtype_microdomain transients in L1 CNS.avi"
        ),
        "id": "fig1video2",
        "filename": "elife-58962-fig1-video2.avi",
    },
    {
        "comment": "Example of Supplementary Video",
        "article_id": 43542,
        "title": "Figure 9 - Supplementary Video 1",
        "upload_file_nm": "supp_figure9_video1.mp4",
        "id": "fig9video1",
        "filename": "elife-43542-fig9-video1.mp4",
    },
    {
        "comment": "Example of extra whitespace",
        "article_id": 51221,
        "title": "Video  1",
        "upload_file_nm": "video 1.mp4",
        "id": "video1",
        "filename": "elife-51221-video1.mp4",
    },
    {
        "comment": "Example of no whitespace",
        "article_id": 58145,
        "title": "Figure2-Video1",
        "upload_file_nm": "Figure2Movie1.mp4",
        "id": "fig2video1",
        "filename": "elife-58145-fig2-video1.mp4",
    },
    {
        "comment": "Example with underscore",
        "article_id": 62047,
        "title": "Video_10",
        "upload_file_nm": "Video_10.mp4",
        "id": "video10",
        "filename": "elife-62047-video10.mp4",
    },
    {
        "comment": "Example with underscore and two elements",
        "article_id": 63755,
        "title": "Figure 7_video 1",
        "upload_file_nm": "Figure 7Video 1_Custodio et al_time lapse of colony in Fig.7A.avi",
        "id": "fig7video1",
        "filename": "elife-63755-fig7-video1.avi",
    },
    {
        "comment": "Example with a file extension",
        "article_id": 58626,
        "title": "Figure 1 Video 1.mp4",
        "upload_file_nm": "Figure 1_Video 1.mp4",
        "id": "fig1video1",
        "filename": "elife-58626-fig1-video1.mp4",
    },
    {
        "comment": "Example of a longer title",
        "article_id": 40033,
        "title": "Figure 7-video 2. Murine Fgf2 +/+ hematopoietic progenitors and ....",
        "upload_file_nm": "mouse DiI KO exosomes  DiO WT BM lin neg.mov",
        "id": "fig7video2",
        "filename": "elife-40033-fig7-video2.mov",
    },
    {
        "comment": "Example of missing number",
        "article_id": 99999,
        "title": "Figure - Video 1",
        "upload_file_nm": "video.mp4",
        "id": None,
        "filename": None,
    },
    {
        "comment": "Example of a non-numeric figure number",
        "article_id": 65234,
        "title": "Figure 6A-video 1",
        "upload_file_nm": "Figure 6A Video 1.mp4",
        "id": None,
        "filename": None,
    },
    {
        "comment": "Example of missing video term",
        "article_id": 42823,
        "title": "Figure 3-figure supplement 2",
        "upload_file_nm": (
            "Figure 3figure supplement 2. "
            "Six Chromosome FISH of a C. elegans intestinal nucleus.mp4"
        ),
        "id": None,
        "filename": None,
    },
    {
        "comment": "Example of video typo",
        "article_id": 47346,
        "title": "Vidoe 5",
        "upload_file_nm": "Video 5.mp4",
        "id": None,
        "filename": None,
    },
    {
        "comment": "Example of irregular title value",
        "article_id": 53777,
        "title": "Potential Striking Image- Live and dynamic IP",
        "upload_file_nm": "INP_DNeDMS_004 copy.mp4",
        "id": None,
        "filename": None,
    },
]

VIDEO_FILES_EXAMPLE = [
    OrderedDict(
        [
            ("file_type", "video"),
            ("upload_file_nm", "Video 1 AVI.avi"),
            (
                "custom_meta",
                [
                    OrderedDict(
                        [
                            ("meta_name", "Title"),
                            ("meta_value", "Video 1"),
                        ]
                    )
                ],
            ),
        ]
    ),
    OrderedDict(
        [
            ("file_type", "video"),
            ("upload_file_nm", "Video 2 AVI.avi"),
            (
                "custom_meta",
                [
                    OrderedDict(
                        [
                            ("meta_name", "Title"),
                            ("meta_value", "Audio 1"),
                        ]
                    )
                ],
            ),
        ]
    ),
    OrderedDict(
        [
            ("file_type", "figure"),
            ("upload_file_nm", "eLife64719_figure1_classB.png"),
            (
                "custom_meta",
                [
                    OrderedDict(
                        [
                            ("meta_name", "Figure number"),
                            ("meta_value", "Figure 1"),
                        ]
                    ),
                    OrderedDict(
                        [
                            ("meta_name", "Title"),
                            ("meta_value", "Figure 1"),
                        ]
                    ),
                ],
            ),
        ]
    ),
]


class TestVideoFileList(unittest.TestCase):
    def test_video_file_list(self):
        files = VIDEO_FILES_EXAMPLE
        expected = VIDEO_FILES_EXAMPLE[0:2]
        self.assertEqual(video.video_file_list(files), expected)


class TestCollectVideoData(unittest.TestCase):
    def test_collect_video_data(self):
        files = VIDEO_FILES_EXAMPLE
        expected = [
            OrderedDict([("upload_file_nm", "Video 1 AVI.avi"), ("title", "Video 1")]),
            OrderedDict([("upload_file_nm", "Video 2 AVI.avi"), ("title", "Audio 1")]),
        ]
        self.assertEqual(video.collect_video_data(files), expected)


class TestRenameVideoData(unittest.TestCase):
    def test_rename_video_data(self):
        article_id = "3"
        video_data = [{"upload_file_nm": "Video 1.ogv", "title": "Figure 1 - Video 1"}]
        expected = [
            OrderedDict(
                [
                    ("upload_file_nm", "Video 1.ogv"),
                    ("video_id", "fig1video1"),
                    ("video_filename", "elife-00003-fig1-video1.ogv"),
                ]
            )
        ]
        self.assertEqual(video.rename_video_data(video_data, article_id), expected)


class TestVideoDataFromFiles(unittest.TestCase):
    def test_video_data_from_files(self):
        article_id = "3"
        files = VIDEO_FILES_EXAMPLE
        expected = [
            OrderedDict(
                [
                    ("upload_file_nm", "Video 1 AVI.avi"),
                    ("video_id", "video1"),
                    ("video_filename", "elife-00003-video1.avi"),
                ]
            ),
            OrderedDict(
                [
                    ("upload_file_nm", "Video 2 AVI.avi"),
                    ("video_id", None),
                    ("video_filename", None),
                ]
            ),
        ]
        self.assertEqual(video.video_data_from_files(files, article_id), expected)

    def test_video_data_from_files_empty(self):
        files = [""]
        article_id = "3"
        expected = []
        self.assertEqual(video.video_data_from_files(files, article_id), expected)


class TestAllTermsMap(unittest.TestCase):
    def test_all_terms_map(self):
        video_data = [
            OrderedDict(
                [
                    ("upload_file_nm", "Video 1.ogv"),
                    ("title", "Figure 1 - Video 1"),
                ]
            ),
            OrderedDict(
                [
                    ("upload_file_nm", "Video 2.mp4"),
                    ("title", "Figure 1 - Video 2"),
                ]
            ),
            OrderedDict(
                [
                    ("upload_file_nm", "Appendix 2 Video 1.mp4"),
                    ("title", "Appendix 2 Video 1"),
                ]
            ),
        ]

        expected = OrderedDict(
            [
                (
                    "Video 1.ogv",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "1")]),
                    ],
                ),
                (
                    "Video 2.mp4",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "2")]),
                    ],
                ),
                (
                    "Appendix 2 Video 1.mp4",
                    [
                        OrderedDict([("name", "app"), ("number", "2")]),
                        OrderedDict([("name", "video"), ("number", "1")]),
                    ],
                ),
            ]
        )
        all_terms = video.all_terms_map(video_data)
        self.assertEqual(all_terms, expected, "got all_terms: %s" % all_terms)

    def test_all_terms_map_duplicate(self):
        "check return value when there is a duplicate video file name"
        video_data = [
            OrderedDict(
                [
                    ("upload_file_nm", "Video 2.ogv"),
                    ("title", "Figure 1 - Video 2"),
                ]
            ),
            OrderedDict(
                [
                    ("upload_file_nm", "Supplementary Video 2.mp4"),
                    ("title", "Figure 1 - Supplementary Video 2"),
                ]
            ),
            OrderedDict(
                [
                    ("upload_file_nm", "Video 1.mp4"),
                    ("title", "Figure 1 - Video 1"),
                ]
            ),
        ]
        # note the term values are now unique, the duplicate value is renumbered
        expected = OrderedDict(
            [
                (
                    "Video 2.ogv",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "2")]),
                    ],
                ),
                (
                    "Supplementary Video 2.mp4",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "3")]),
                    ],
                ),
                (
                    "Video 1.mp4",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "1")]),
                    ],
                ),
            ]
        )
        all_terms = video.all_terms_map(video_data)
        self.assertEqual(all_terms, expected, "got all_terms: %s" % all_terms)


class TestRenumberTermMap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_renumber_term_map(self):
        configure_logging(self.log_file)
        term_map = OrderedDict(
            [
                (
                    "Video 2.ogv",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "2")]),
                    ],
                ),
                (
                    "Supplementary Video 2.mp4",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "2")]),
                    ],
                ),
                (
                    "Video 1.mp4",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "1")]),
                    ],
                ),
            ]
        )
        prefix_to_keys_map = {
            "fig1video": ["Video 2.ogv", "Supplementary Video 2.mp4", "Video 1.mp4"]
        }

        expected = OrderedDict(
            [
                (
                    "Video 2.ogv",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "2")]),
                    ],
                ),
                (
                    "Supplementary Video 2.mp4",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "3")]),
                    ],
                ),
                (
                    "Video 1.mp4",
                    [
                        OrderedDict([("name", "fig"), ("number", "1")]),
                        OrderedDict([("name", "video"), ("number", "1")]),
                    ],
                ),
            ]
        )
        info_prefix = "INFO elifecleaner:video:renumber_term_map:"
        expected_log_file_line = (
            "%s replacing number 2 with 3 for term Supplementary Video 2.mp4\n"
            % info_prefix
        )

        new_term_map = video.renumber_term_map(term_map, prefix_to_keys_map)
        self.assertEqual(new_term_map, expected)
        self.assertEqual(read_log_file_lines(self.log_file)[-1], expected_log_file_line)


class TestRenumberKeyMap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"
        self.log_file = os.path.join(self.temp_dir, "test.log")
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_renumber_key_map(self):
        configure_logging(self.log_file)
        prefix = "fig1video"
        key_map = OrderedDict(
            [
                ("Video 2.ogv", 2),
                ("Supplementary Video 2.mp4", 2),
                ("Video 1.mp4", 1),
            ]
        )

        expected = OrderedDict(
            [
                ("Video 2.ogv", 2),
                ("Supplementary Video 2.mp4", 3),
                ("Video 1.mp4", 1),
            ]
        )
        info_prefix = "INFO elifecleaner:video:renumber_key_map:"
        expected_log_file_lines = [
            "%s number values used for video prefix fig1video: [2, 2, 1]\n"
            % info_prefix,
            "%s duplicate number values for video prefix fig1video: [2]\n"
            % info_prefix,
            "%s replacement number values can be used for video prefix fig1video: [3]\n"
            % info_prefix,
        ]
        new_key_map = video.renumber_key_map(prefix, key_map)
        self.assertEqual(new_key_map, expected)
        self.assertEqual(read_log_file_lines(self.log_file), expected_log_file_lines)


class TestTermsFromTitle(unittest.TestCase):
    def test_terms_from_title(self):
        title = (
            "Animation 999 "
            "- Video 2 "
            "- Appendix 3 "
            "- Figure 4 "
            "- Figure Supplement 5 "
            "- Video Supplement 6 "
            "- Videos Supplement 7 "
            "- Supplementary Video 8 "
            "Figure-4-Video 2"
            "- Vidoe 9"
        )
        expected = [
            OrderedDict([("name", "video"), ("number", "999")]),
            OrderedDict([("name", "video"), ("number", "2")]),
            OrderedDict([("name", "app"), ("number", "3")]),
            OrderedDict([("name", "fig"), ("number", "4")]),
            OrderedDict([("name", "video"), ("number", "6")]),
            OrderedDict([("name", "video"), ("number", "7")]),
            OrderedDict([("name", "video"), ("number", "8")]),
            OrderedDict([("name", "fig"), ("number", "4")]),
            OrderedDict([("name", "video"), ("number", "2")]),
        ]

        self.assertEqual(video.terms_from_title(title), expected)

    def test_terms_from_title_empty_string(self):
        title = ""
        expected = []
        self.assertEqual(video.terms_from_title(title), expected)


class TestVideoId(unittest.TestCase):
    def test_video_id(self):
        for test_data in VIDEO_TITLE_EXAMPLES:
            self.assertEqual(
                video.video_id(test_data.get("title")), test_data.get("id")
            )


class TestVideoFilename(unittest.TestCase):
    def test_video_filename(self):
        for test_data in VIDEO_TITLE_EXAMPLES:
            self.assertEqual(
                video.video_filename(
                    test_data.get("title"),
                    test_data.get("upload_file_nm"),
                    test_data.get("article_id"),
                ),
                test_data.get("filename"),
                "title: %s" % test_data.get("title"),
            )
