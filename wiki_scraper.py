#No Ai implementation here, just web scraping logic
from playwright.sync_api import sync_playwright, TimeoutError

def get_wikipedia_article(search_term: str) -> dict:

    result = {"intro": "", "infobox": ""}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Go to Wikipedia homepage
            page.goto("https://www.wikipedia.org/")

            # Type the search term and press Enter
            page.fill("input[name='search']", search_term)
            page.press("input[name='search']", "Enter")

            # Wait for the article content to load
            page.wait_for_selector("#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)", timeout=10000)

            # Grab first 2-3 paragraphs as intro
            paragraphs = page.query_selector_all("#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)")
            intro_text = "\n\n".join(p.inner_text() for p in paragraphs[:3])
            result["intro"] = intro_text

            # Grab infobox if it exists for extra information
            infobox_elem = page.query_selector("table.infobox")
            if infobox_elem:
                result["infobox"] = infobox_elem.inner_text()

        except TimeoutError:
            result["intro"] = "Error: Could not find article content."
        except Exception as e:
            result["intro"] = f"Error: {e}"
        finally:
            browser.close()

    return result


if __name__ == "__main__":
    term = input("Enter a Wikipedia search term: ").strip()
    article = get_wikipedia_article(term)
    print("\n--- INTRO ---\n")
    print(article["intro"])
    print("\nSuccess! Article scraped.")
else:
     print("Failed to scrape article.")


