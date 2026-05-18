from playwright.async_api import async_playwright


async def extract_page_elements(url: str):

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page()

        await page.goto(url, wait_until="domcontentloaded")

        # PAGE TITLE
        title = await page.title()

        # BUTTONS
        button_elements = await page.locator("button").evaluate_all(
            """
            elements => elements.map(el => ({
                text: el.innerText?.trim() || "",
                aria_label: el.getAttribute("aria-label") || "",
                id: el.id || "",
                class: el.className || "",
                type: el.getAttribute("type") || "",
                name: el.getAttribute("name") || "",
                role: el.getAttribute("role") || "",
                data_testid: el.getAttribute("data-testid") || ""
            }))
            """
        )

        # INPUTS
        input_elements = await page.locator("input").evaluate_all(
            """
            elements => elements.map(el => ({
                name: el.name || "",
                type: el.type || "",
                placeholder: el.placeholder || "",
                id: el.id || ""
            }))
            """
        )

        # INPUT BUTTONS / SUBMITS
        submit_buttons = await page.locator(
            "input[type='submit'], input[type='button']"
        ).evaluate_all(
            """
            elements => elements.map(el => ({
                text: el.value || "",
                aria_label: el.getAttribute("aria-label") || "",
                id: el.id || "",
                class: el.className || "",
                type: el.type || "",
                name: el.name || "",
                role: el.getAttribute("role") || "",
                data_testid: el.getAttribute("data-testid") || ""
            }))
            """
        )

        button_elements.extend(submit_buttons)

        # HEADINGS
        headings = await page.locator("h1, h2, h3").all_inner_texts()

        # LINKS
        links = await page.locator("a").evaluate_all(
            """
            elements => elements.slice(0, 20).map(el => ({
                text: el.innerText?.trim() || "",
                href: el.href || ""
            }))
            """
        )

        await browser.close()
        print({
            "title": title,
            "buttons": button_elements[:2],
            "inputs": input_elements[:2],
        })

        return {
            "title": title,
            "buttons": button_elements,
            "inputs": input_elements,
            "headings": headings,
            "links": links
        }