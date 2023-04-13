# elife-cleaner

Clean and transform article submission files into a consistent format

## Requirements

Install `imagemagick-dev` and `ghostscript` in order for `wand` Python module to open PDF files. Also, the imagemagick `policy.xml` file must be configured to allow reading of PDF files.

## Configuration

To use a YAML file of assessment terms in the `asessment_terms.py` module, set the constant `ASSESSMENT_TERMS_YAML` in the module to be the path to the YAML file on disk. The sample file `assessment_terms.yaml` in the code repository is not distributed as part of the library.

## License

Licensed under [MIT](https://opensource.org/licenses/mit-license.php).
