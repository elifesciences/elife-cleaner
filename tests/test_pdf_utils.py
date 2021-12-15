import os
import unittest
from mock import patch
from elifecleaner import pdf_utils, zip_lib
from tests.helpers import delete_files_in_folder

PDFIMAGES_OUTPUT = (
    b"page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio\n"
    b"--------------------------------------------------------------------------------------------\n"
    b"   1     0 image    1254  2131  rgb     3   8  image  no         9  0   220   220  139K 1.8%\n"
    b"   2     1 image    1314   358  rgb     3   8  image  no        12  0   223   222 18.0K 1.3%\n"
    b"   2     2 image    1324   361  rgb     3   8  image  no        13  0   224   224 21.0K 1.5%\n"
    b"   2     3 image    1319   360  rgb     3   8  image  no        14  0   223   224 21.5K 1.5%\n"
    b"   2     4 image    1319   360  rgb     3   8  image  no        15  0   223   224 19.0K 1.4%\n"
    b"   2     5 image    1314   358  rgb     3   8  image  no        16  0   223   222 18.5K 1.3%\n"
    b"   3     6 image    1321   360  rgb     3   8  image  no        19  0   224   223 23.5K 1.7%\n"
    b"   3     7 image    1328   362  rgb     3   8  image  no        20  0   225   225 23.5K 1.7%\n"
    b"   3     8 image    1328   362  rgb     3   8  image  no        21  0   225   225 20.8K 1.5%\n"
    b"   3     9 image    1324   361  rgb     3   8  image  no        22  0   224   224 21.9K 1.6%\n"
    b"   3    10 image    1328   362  rgb     3   8  image  no        23  0   225   225 23.9K 1.7%\n"
    b"   4    11 image    1330   363  rgb     3   8  image  no        26  0   225   225 21.5K 1.5%\n"
    b"   4    12 image    1326   362  rgb     3   8  image  no        27  0   225   225 24.9K 1.8%\n"
    b"   4    13 image    1326   362  rgb     3   8  image  no        28  0   225   225 26.3K 1.9%\n"
    b"   4    14 image    1331   360  rgb     3   8  image  no        29  0   225   225 29.7K 2.1%\n"
    b"   4    15 image    1330   363  rgb     3   8  image  no        30  0   225   225 24.2K 1.7%\n"
    b"   5    16 image    1321   360  rgb     3   8  image  no        33  0   224   223 25.0K 1.8%\n"
    b"   5    17 image    1312   358  rgb     3   8  image  no        34  0   222   222 23.6K 1.7%\n"
    b"   5    18 image    1328   362  rgb     3   8  image  no        35  0   225   225 25.0K 1.8%\n"
    b"   5    19 image    1324   361  rgb     3   8  image  no        36  0   224   224 23.1K 1.6%\n"
    b"   5    20 image    1307   356  rgb     3   8  image  no        37  0   221   221 26.1K 1.9%\n"
    b"   6    21 image    1322   358  rgb     3   8  image  no        40  0   220   220 26.6K 1.9%\n"
    b"   6    22 image    1300   352  rgb     3   8  image  no        41  0   220   220 23.6K 1.8%\n"
    b"   6    23 image    1300   352  rgb     3   8  image  no        42  0   220   220 35.3K 2.6%\n"
    b"   6    24 image    1300   352  rgb     3   8  image  no        43  0   220   220 20.0K 1.5%\n"
    b"   6    25 image    1300   352  rgb     3   8  image  no        44  0   220   220 29.6K 2.2%\n"
)


class Result:
    "struct for testing"

    def __init__(self):
        self.stdout = None


class TestPdfImagePages(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def tearDown(self):
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])

    def test_pdfimages_output(self):
        zip_file = "tests/test_data/30-01-2019-RA-eLife-45644.zip"
        zip_lib.unzip_zip(zip_file, self.temp_dir)
        # run only if pdfimages is available
        if pdf_utils.pdfimages_exists():
            pdf_file = os.path.join(
                self.temp_dir, "30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf"
            )
            result = pdf_utils.pdfimages_output(pdf_file)
            self.assertIsNotNone(result.stdout)

    @patch.object(pdf_utils, "pdfimages_output")
    def test_pdf_image_pages(self, mock_pdfimages_output):
        mock_result = Result()
        mock_result.stdout = PDFIMAGES_OUTPUT
        mock_pdfimages_output.return_value = mock_result
        expected = {1, 2, 3, 4, 5, 6}
        pdf_file = "figure.pdf"
        pages = pdf_utils.pdf_image_pages(pdf_file)
        self.assertEqual(pages, expected)
