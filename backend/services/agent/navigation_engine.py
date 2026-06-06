from urllib.parse import urljoin


IMPORTANT_KEYWORDS = [
    "dashboard",
    "profile",
    "settings",
    "reports",
    "analytics",
    "users",
    "products",
    "admin",
    "login",
    "signup",
    "orders",
]


def score_link(link: dict):

    score = 0

    text = (
        (link.get("text") or "") +
        " " +
        (link.get("href") or "")
    ).lower()

    for keyword in IMPORTANT_KEYWORDS:
        if keyword in text:
            score += 10

    if link.get("href", "").startswith("http"):
        score += 2

    return score


def prioritize_links(links: list):

    ranked = sorted(
        links,
        key=score_link,
        reverse=True
    )

    return ranked