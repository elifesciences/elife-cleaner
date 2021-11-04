from collections import OrderedDict


EXPECTED = [
    OrderedDict(
        [
            ("file_type", "aux_file"),
            ("id", "1119366"),
            ("upload_file_nm", "Figure 5source code 1.c"),
            (
                "custom_meta",
                [
                    OrderedDict(
                        [
                            ("meta_name", "Title"),
                            ("meta_value", "Figure 5-source code 1"),
                        ]
                    )
                ],
            ),
        ]
    ),
    OrderedDict(
        [
            ("file_type", "aux_file"),
            ("id", None),
            ("upload_file_nm", "Figure 5source code 2.c"),
            (
                "custom_meta",
                [
                    OrderedDict(
                        [
                            ("meta_name", "Title"),
                            ("meta_value", "Figure 5-source code 2"),
                        ]
                    )
                ],
            ),
        ]
    ),
]
