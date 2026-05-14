from urllib.parse import urlparse


def is_same_domain(base_url: str, current_url: str):
    base_domain = urlparse(base_url).netloc
    current_domain = urlparse(current_url).netloc

    return base_domain == current_domain