import os
import unittest
from pathlib import Path
from tests.helpers import delete_files_in_folder


class TestHelpers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/tmp"

    def test_delete_files_in_folder(self):
        "test helpers function to clean out tests temp directory"
        file_name = os.path.join(self.temp_dir, "test_file.txt")
        folder_name = os.path.join(self.temp_dir, "test_folder")
        os.mkdir(folder_name)
        Path(file_name).touch()
        delete_files_in_folder(self.temp_dir, filter_out=[".keepme"])
        self.assertEqual(len(os.listdir(self.temp_dir)), 1)
