from collections import OrderedDict

EXPECTED = OrderedDict(
    [
        (
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.pdf",
            "tests/tmp/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.pdf",
        ),
        (
            "30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
            "tests/tmp/30-01-2019-RA-eLife-45644/30-01-2019-RA-eLife-45644.xml",
        ),
        (
            "30-01-2019-RA-eLife-45644/Answers for the eLife digest.docx",
            "tests/tmp/30-01-2019-RA-eLife-45644/Answers for the eLife digest.docx",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1.docx",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1.docx",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 1.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 1.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 10.pdf",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 11.pdf",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 12.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 12.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 13.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 13.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 14.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 14.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 15.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 15.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 2.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 2.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 3.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 3.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 4.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 4.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 5.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 5.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 6.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 6.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 7.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 7.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 8.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 8.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Appendix 1figure 9.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Appendix 1figure 9.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 1.tif",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 1.tif",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 2.tif",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 2.tif",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 3.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 3.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 4.svg",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 4.svg",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 4source data 1.zip",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 4source data 1.zip",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 5.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 5.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 5source code 1.c",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 5source code 1.c",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 10_HorC.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 10_HorC.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 1_U crassus.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 1_U crassus.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 2_U pictorum.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 2_U pictorum.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 3_M margaritifera.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 3_M margaritifera.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 4_P auricularius.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 4_P auricularius.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 5_PesB.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 5_PesB.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 6_HavA.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 6_HavA.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 7_HavB.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 7_HavB.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 8_HavC.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 8_HavC.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6figure supplement 9_HorB.png",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6figure supplement 9_HorB.png",
        ),
        (
            "30-01-2019-RA-eLife-45644/Figure 6source data 1.pdf",
            "tests/tmp/30-01-2019-RA-eLife-45644/Figure 6source data 1.pdf",
        ),
        (
            "30-01-2019-RA-eLife-45644/Manuscript.docx",
            "tests/tmp/30-01-2019-RA-eLife-45644/Manuscript.docx",
        ),
        (
            "30-01-2019-RA-eLife-45644/Potential striking image.tif",
            "tests/tmp/30-01-2019-RA-eLife-45644/Potential striking image.tif",
        ),
        (
            "30-01-2019-RA-eLife-45644/Table 2source data 1.xlsx",
            "tests/tmp/30-01-2019-RA-eLife-45644/Table 2source data 1.xlsx",
        ),
        (
            "30-01-2019-RA-eLife-45644/transparent_reporting_Sakalauskaite.docx",
            "tests/tmp/30-01-2019-RA-eLife-45644/transparent_reporting_Sakalauskaite.docx",
        ),
    ]
)
