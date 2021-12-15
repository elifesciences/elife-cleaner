import re
import shutil
import subprocess


def pdfimages_exists():
    "check if pdfimages exists"
    return shutil.which("pdfimages")


def pdfimages_output(pdf):
    "invoke pdfimages utility"
    return subprocess.run(
        ["pdfimages", "-list", pdf],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def pdf_image_pages(pdf):
    "return pdf pages on which images are found from pdfimages output"
    result = pdfimages_output(pdf)
    page_list = []
    if result.stdout:
        page_line_match_pattern = re.compile(r"\s+(\d+)\s.*")
        output_lines = str(result.stdout, encoding="utf8").split("\n")
        if output_lines and output_lines[0].startswith("page "):
            for line in output_lines:
                match_result = re.match(page_line_match_pattern, line)
                if match_result:
                    page_list.append(int(match_result.group(1)))
    # de-dupe page list into a set of unique values
    return set(page_list)
