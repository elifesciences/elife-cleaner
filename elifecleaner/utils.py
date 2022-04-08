def pad_msid(msid):
    "zerofill string for article_id value"
    return "{:05d}".format(int(msid))
