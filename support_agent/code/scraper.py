import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin, urlparse

class SupportScraper:
    def __init__(self, output_path=None):
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), "..", "data", "corpus", "corpus.json")
        self.output_path = os.path.abspath(output_path)
        self.corpus = []
        self.visited = set()
        self.delay = 0.3

    def get_page(self, url, retries=3):
        for i in range(retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                time.sleep(self.delay)
                return response.text
            except Exception as e:
                print(f"Error fetching {url}: {e}. Retry {i+1}/{retries}")
                time.sleep(1)
        return None

    def scrape_hackerrank(self):
        base_url = "https://support.hackerrank.com"
        start_url = "https://support.hackerrank.com/hc/en-us"
        self._scrape_zendesk(start_url, base_url, "hackerrank")

    def scrape_claude(self):
        base_url = "https://support.claude.com"
        start_url = "https://support.claude.com/en"
        self._scrape_generic(start_url, base_url, "claude")

    def scrape_visa(self):
        base_url = "https://www.visa.co.in"
        start_url = "https://www.visa.co.in/support.html"
        self._scrape_generic(start_url, base_url, "visa")

    def _scrape_zendesk(self, start_url, base_url, source):
        # Zendesk often has a specific structure: /hc/en-us/categories, /hc/en-us/sections, /hc/en-us/articles
        # We'll crawl articles
        print(f"Scraping {source}...")
        page_content = self.get_page(start_url)
        if not page_content: return
        
        soup = BeautifulSoup(page_content, 'html.parser')
        # Find all links that look like articles
        links = soup.find_all('a', href=True)
        article_links = set()
        for link in links:
            href = link['href']
            full_url = urljoin(base_url, href)
            if "/articles/" in full_url and full_url not in self.visited:
                article_links.add(full_url)
        
        for url in article_links:
            self._process_article(url, source)

    def _scrape_generic(self, start_url, base_url, source):
        print(f"Scraping {source}...")
        page_content = self.get_page(start_url)
        if not page_content: return
        
        soup = BeautifulSoup(page_content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        # This is a bit simplified; in a real hackathon you'd want to be more specific
        # but let's try to find potential article links.
        potential_links = set()
        for link in links:
            href = link['href']
            full_url = urljoin(base_url, href)
            # Filter for links within the same support domain and not the index itself
            if urlparse(full_url).netloc == urlparse(base_url).netloc and full_url != start_url:
                if any(x in full_url.lower() for x in ['article', 'help', 'support', 'faq', 'guide']):
                     potential_links.add(full_url)

        for url in potential_links:
            if url not in self.visited:
                self._process_article(url, source)

    def _process_article(self, url, source):
        if url in self.visited: return
        self.visited.add(url)
        
        content = self.get_page(url)
        if not content: return
        
        soup = BeautifulSoup(content, 'html.parser')
        
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "No Title"
        
        # Try to find the main article body
        # Common classes for Zendesk and others
        body = soup.find('article') or soup.find('div', class_='article-body') or soup.find('div', class_='content') or soup.body
        
        article_text = ""
        if body:
            # Remove scripts and styles
            for script in body(["script", "style"]):
                script.decompose()
            article_text = body.get_text(separator=' ', strip=True)
        
        # Truncate to 4000 chars
        article_text = article_text[:4000]
        
        # Optional breadcrumb
        breadcrumb = ""
        bc_element = soup.find('ol', class_='breadcrumbs') or soup.find('nav', class_='breadcrumbs')
        if bc_element:
            breadcrumb = bc_element.get_text(separator=' > ', strip=True)

        self.corpus.append({
            "source": source,
            "url": url,
            "title": title,
            "content": article_text,
            "breadcrumb": breadcrumb
        })
        print(f"  Saved: {title} ({url})")

    def save(self):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.corpus, f, indent=2)
        print(f"Scraping complete. Total articles: {len(self.corpus)}")

def main():
    scraper = SupportScraper()
    scraper.scrape_hackerrank()
    scraper.scrape_claude()
    scraper.scrape_visa()
    scraper.save()

if __name__ == "__main__":
    main()
