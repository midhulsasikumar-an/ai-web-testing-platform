def test_links(page):
    try:
        links = page.query_selector_all("a")
        broken = []

        for link in links[:15]:
            href = link.get_attribute("href")

            if not href:
                broken.append("empty href")

        if broken:
            return {
                "test": "Links Check",
                "status": "fail",
                "details": f"{len(broken)} broken links"
            }

        return {
            "test": "Links Check",
            "status": "pass",
            "details": "No broken links"
        }

    except Exception as e:
        return {"test": "Links Check", "status": "fail", "error": str(e)}
