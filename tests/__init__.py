import logging

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s %(message)s"))
handler.addFilter(logging.Filter("algokit_subscriber"))

logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
