#This file contains the AI logic to generate a plan and execute it and REQUIRES an OpenAI API Key see README.MD for setup
from dotenv import load_dotenv
import os
import openai
import json
from playwright.sync_api import sync_playwright, TimeoutError

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ask user what they want info on
goal = input("Enter a Wikipedia search goal or a famous person: ").strip()

# Grab the main page elements to help the AI plan
def get_page_context(page):
    context = {
        "inputs": [i.get_attribute("name") or i.get_attribute("id") 
                   for i in page.query_selector_all("input")],
        "buttons": [b.inner_text() for b in page.query_selector_all("button")],
        "links": [a.get_attribute("href") for a in page.query_selector_all("a")],
        "headings": [h.inner_text() for h in page.query_selector_all("h1, h2, h3, h4, h5, h6")]
    }
    return context

# Ask OpenAI for a plan
def ask_llm_for_plan(goal, page_context):
    prompt = (
        f"User wants to: '{goal}'\n"
        f"Page info: {json.dumps(page_context)}\n"
        "Give a step-by-step plan in JSON using these actions:\n"
        "- goto (navigate to URL)\n"
        "- fill (input text, needs selector & value)\n"
        "- press (press a key, needs selector & value)\n"
        "- extract (get text, needs selector)\n"
        "Return only valid JSON array of steps.\n"
        "Example: [{\"action\": \"fill\", \"selector\": \"input[name='search']\", \"value\": \"Kanye West\"}]"
    )
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Clean up any messy JSON from GPT
def clean_gpt_json(raw_json):
    try:
        data = json.loads(raw_json)
        return [step for step in data if isinstance(step, dict) and "action" in step]
    except json.JSONDecodeError:
        return []

# Start browser and run the AI plan
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Go to Wikipedia and get the context
    page.goto("https://www.wikipedia.org/")
    context = get_page_context(page)

    # Get AI plan
    raw_plan = ask_llm_for_plan(goal, context)
    steps = clean_gpt_json(raw_plan)

    # Make sure we extract a summary
    if not any(s.get("action") == "extract" for s in steps):
        steps.append({
            "action": "extract",
            "selector": "#mw-content-text .mw-parser-output > p:not(.mw-empty-elt)"
        })

    print("\nAI Plan Generated:")
    print(json.dumps(steps, indent=2))

    # Run the steps based on the actions
    summary = []
    for step in steps:
        action = step.get("action")
        selector = step.get("selector") or step.get("value", "")
        value = step.get("value", "")

        try:
            if action == "goto":
                url = step.get("value") or step.get("url")
                print(f"Going to {url}")
                page.goto(url)
            elif action == "fill":
                print(f"Filling {selector} with {value}")
                page.fill(selector, value)
            elif action == "press":
                key = value if value else "Enter"
                print(f"Pressing {key} on {selector}")
                page.press(selector, key)
            elif action == "extract":
                print(f"Extracting text from {selector}")
                page.wait_for_selector(selector, timeout=10000)
                elements = page.query_selector_all(selector)
                for el in elements[:2]:  
                    text = el.inner_text().strip()
                    if text:
                        summary.append(text)
        except TimeoutError:
            print(f"Timeout on {action} for {selector}")
        except Exception as e:
            print(f"Error on step {step}: {e}")

    browser.close()

    # Show the summary
    print("\n--- SUMMARY ---\n")
    print("\n\n".join(summary))
