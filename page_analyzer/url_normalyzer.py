from urllib.parse import urlparse


def normalize_url(raw_url):
    parsed = urlparse(raw_url)
    return f'{parsed.scheme}://{parsed.netloc}'
