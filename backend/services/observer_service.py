from playwright.async_api import Page

# ---------------------------------------------------
# BUTTONS
# ---------------------------------------------------

async def extract_buttons(page: Page):

    elements = await page.locator(
        "button, input[type='submit'], [role='button']"
    ).all()

    results = []

    for el in elements[:50]:

        try:
            text = (await el.inner_text()).strip()

        except:
            text = ""

        results.append({
            "text": text,
            "selector": await generate_selector(el)
        })

    return results


# ---------------------------------------------------
# LINKS
# ---------------------------------------------------

async def extract_links(page: Page):

    elements = await page.locator("a").all()

    results = []

    for el in elements[:100]:

        try:
            text = (await el.inner_text()).strip()
            href = await el.get_attribute("href")

        except:
            continue

        if not text and not href:
            continue

        results.append({
            "text": text,
            "href": href
        })

    return results


# ---------------------------------------------------
# INPUTS
# ---------------------------------------------------

async def extract_inputs(page: Page):

    elements = await page.locator(
        "input, textarea, select"
    ).all()

    results = []

    for el in elements[:50]:

        try:
            input_type = await el.get_attribute("type")
            name = await el.get_attribute("name")
            placeholder = await el.get_attribute("placeholder")

            results.append({
                "type": input_type,
                "name": name,
                "placeholder": placeholder,
                "selector": await generate_selector(el)
            })

        except:
            continue

    return results


# ---------------------------------------------------
# HEADINGS
# ---------------------------------------------------

async def extract_headings(page: Page):

    elements = await page.locator(
        "h1, h2, h3"
    ).all()

    results = []

    for el in elements[:20]:

        try:
            text = (await el.inner_text()).strip()

            if text:
                results.append(text)

        except:
            continue

    return results


# ---------------------------------------------------
# FORMS
# ---------------------------------------------------

async def extract_forms(page: Page):

    forms = await page.locator("form").all()

    results = []

    for form in forms:

        try:
            inputs = await form.locator(
                "input"
            ).all()

            fields = []

            for inp in inputs:

                fields.append({
                    "name": await inp.get_attribute("name"),
                    "type": await inp.get_attribute("type"),
                    "placeholder": await inp.get_attribute("placeholder")
                })

            results.append({
                "fields": fields
            })

        except:
            continue

    return results


# ---------------------------------------------------
# ERRORS
# ---------------------------------------------------

async def extract_errors(page: Page):

    possible_error_selectors = [
        ".error",
        ".alert",
        "[role='alert']",
        ".text-red-500",
        ".invalid-feedback"
    ]

    errors = []

    for selector in possible_error_selectors:

        try:
            elements = await page.locator(selector).all()

            for el in elements:

                text = (await el.inner_text()).strip()

                if text:
                    errors.append(text)

        except:
            continue

    return errors


# ---------------------------------------------------
# PAGE TYPE DETECTION
# ---------------------------------------------------

def detect_page_type(
    title,
    url,
    forms,
    headings
):

    combined = (
        title +
        " " +
        url +
        " " +
        " ".join(headings)
    ).lower()

    if "login" in combined or "sign in" in combined:
        return "login_page"

    if "register" in combined or "signup" in combined:
        return "signup_page"

    if "dashboard" in combined:
        return "dashboard"

    if len(forms) > 0:
        return "form_page"

    return "generic_page"


# ---------------------------------------------------
# SELECTOR GENERATION
# ---------------------------------------------------

async def generate_selector(el):

    try:
        testid = await el.get_attribute("data-testid")

        if testid:
            return f'[data-testid="{testid}"]'

        aria = await el.get_attribute("aria-label")

        if aria:
            return f'[aria-label="{aria}"]'

        text = (await el.inner_text()).strip()

        if text:
            return f'text="{text}"'

        element_id = await el.get_attribute("id")

        if element_id:
            return f'#{element_id}'

    except:
        pass

    return None

def detect_primary_actions(
    buttons,
    links
):

    important_keywords = [
        "login",
        "sign in",
        "submit",
        "save",
        "update",
        "delete",
        "create",
        "add",
        "dashboard",
        "profile",
        "settings"
    ]

    actions = []

    for btn in buttons:

        text = (
            btn.get("text") or ""
        ).lower()

        if any(
            keyword in text
            for keyword in important_keywords
        ):

            actions.append({
                "type": "button",
                "text": btn.get("text"),
                "selector": btn.get("selector")
            })

    for link in links:

        text = (
            link.get("text") or ""
        ).lower()

        if any(
            keyword in text
            for keyword in important_keywords
        ):

            actions.append({
                "type": "link",
                "text": link.get("text"),
                "href": link.get("href")
            })

    return actions

def extract_navigation_candidates(links):

    ignored_keywords = [
        "logout",
        "delete",
        "remove"
    ]

    candidates = []

    for link in links:

        text = (
            link.get("text") or ""
        ).lower()

        href = (
            link.get("href") or ""
        )

        if not href:
            continue

        if any(
            keyword in text
            for keyword in ignored_keywords
        ):
            continue

        candidates.append({
            "text": link.get("text"),
            "href": href
        })

    return candidates[:20]


async def observe_page(page: Page):

    title = await page.title()
    url = page.url

    buttons = await extract_buttons(page)
    links = await extract_links(page)
    inputs = await extract_inputs(page)
    headings = await extract_headings(page)
    forms = await extract_forms(page)
    errors = await extract_errors(page)

    page_type = detect_page_type(
        title=title,
        url=url,
        forms=forms,
        headings=headings
    )
    primary_actions = detect_primary_actions(
        buttons,    
        links
    )   

    navigation_candidates = extract_navigation_candidates(
        links
    )

    return {
        "title": title,
        "url": url,
        "page_type": page_type,
        "buttons": buttons,
        "links": links,
        "inputs": inputs,
        "forms": forms,
        "headings": headings,
        "errors": errors,
        "primary_actions": primary_actions,
        "navigation_candidates": navigation_candidates,
        "interactive_elements_count": (
            len(buttons) +
            len(inputs) +
            len(links)
        )
    }


