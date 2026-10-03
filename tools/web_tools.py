import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import urllib3
from typing import List, Dict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def scrape_webpage_content(url: str, max_chars: int = 5000) -> str:
    """Fetches a web page URL and extracts the clean readable article text and headings."""
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            
        res = requests.get(url, headers=HEADERS, timeout=12, verify=False)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Remove scripts, styles, navigations, footers
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
            tag.decompose()
            
        # Get title
        title = soup.title.string.strip() if soup.title else "Untitled Page"
        
        # Extract main text
        paragraphs = []
        for elem in soup.find_all(["h1", "h2", "h3", "p", "li", "td", "th"]):
            text = elem.get_text(strip=True)
            if text and len(text) > 20:
                paragraphs.append(text)
                
        body_text = "\n\n".join(paragraphs)
        if not body_text:
            body_text = soup.get_text(separator="\n", strip=True)
            
        # Clean extra whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', body_text)
        
        result = f"PAGE TITLE: {title}\nURL: {url}\n\nCONTENT:\n{cleaned[:max_chars]}"
        if len(cleaned) > max_chars:
            result += "\n... [Content truncated]"
        return result
    except Exception as e:
        return f"Error scraping URL '{url}': {str(e)}"

def search_web_quick(query: str, max_results: int = 4) -> str:
    """Searches DuckDuckGo for top web results without requiring an API key."""
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        results = []
        for r in soup.select(".result"):
            title_tag = r.select_one(".result__title .result__url") or r.select_one(".result__title")
            snippet_tag = r.select_one(".result__snippet")
            link_tag = r.select_one(".result__url")
            
            if title_tag and snippet_tag:
                title = title_tag.get_text(strip=True)
                snippet = snippet_tag.get_text(strip=True)
                href = link_tag.get("href", "").strip() if link_tag else ""
                results.append(f"• {title}\n  Summary: {snippet}\n  Link: {href}")
                if len(results) >= max_results:
                    break
                    
        if not results:
            # Fallback direct query extraction
            return f"No direct search results parsed for '{query}'. Try fetching a specific URL directly."
            
        return f"Search Results for '{query}':\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"Search failed for '{query}': {str(e)}"
