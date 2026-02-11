from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

class HtmlCleaner:
    def __init__(self, link):
        self.link = link
    
    def connect(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless = True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            page = context.new_page()

            page.goto(self.link, wait_until="domcontentloaded", timeout=10000)
            html = page.content()

            block_signals = [
                "captcha", "verify you are human", "access denied",
                "bot detection", "unusual traffic", "blocked",
                "/captcha/", "/robots", "are you a robot"
            ]

            lower_html = html.lower()
            print(any(sig in lower_html for sig in block_signals))
            if any(sig in lower_html for sig in block_signals):
                browser.close()
                return False

            page.evaluate("""
                document.querySelectorAll(
                    'script, style, noscript, iframe, svg'
                ).forEach(el => el.remove());
            """)

            browser.close()

            return html

    def clean_html(self, html):
        soup = BeautifulSoup(html, "lxml")

        for tag in soup([
            "script", "style", "noscript", "iframe", "svg"
        ]):
            tag.decompose()
        return soup
    
    def extract_sections(self, soup):
        sections = []
        current_section = {
            "title": None,
            "content": []
        }

        for el in soup.body.descendants:
            if el.name in ["h1", "h2", "h3", "h4"]:
                if current_section["content"]:
                    sections.append(current_section)

                current_section = {
                    "title": el.get_text(strip=True),
                    "content": []
                }
            
            elif el.name in ["p", "li"]:
                text = el.get_text(" ", strip=True)
                if len(text) > 30:
                    current_section["content"].append(text)

        if current_section["content"]:
            sections.append(current_section)

        return sections
    
    def normalize_text(self, text):
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def remove_repetitions(self, sections):
        seen = set()
        cleaned = []

        for s in sections:
            unique_content = []
            for line in s["content"]:
                if line not in seen:
                    unique_content.append(line)
                    seen.add(line)

            if unique_content:
                cleaned.append({
                    "title": s["title"],
                    "content": unique_content
                })
        
        return cleaned
    