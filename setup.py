from setuptools import setup

import elifecleaner

with open("README.md") as fp:
    readme = fp.read()

setup(
    name="elifecleaner",
    version=elifecleaner.__version__,
    description="Clean and transform article submission files into a consistent format.",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=["elifecleaner"],
    license="MIT",
    install_requires=[
        "docmaptools>=0.26.0",
        "elifetools>=0.40.0",
        "elifearticle>=0.20.0",
        "jatsgenerator>=0.16.0",
        "PyYAML>=5.4.1",
        "wand >= 0.5.2",
    ],
    url="https://github.com/elifesciences/elife-cleaner",
    maintainer="eLife Sciences Publications Ltd.",
    maintainer_email="tech-team@elifesciences.org",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
)
