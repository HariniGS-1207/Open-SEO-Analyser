import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import urllib3
urllib3.disable_warnings()

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your",
    "have", "are", "not", "but", "use", "you", "all", "any", "can",
    "will", "was", "has", "its", "also", "more", "than", "when",
}

def test_scraper(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = requests.get(url, headers=headers, timeout=10, verify=False, allow_redirects=True)
    soup = BeautifulSoup(r.text, "html.parser")

    # Extract Title - try multiple methods
    title = ""
    title_tag = soup.title
    if title_tag and title_tag.string:
        title = title_tag.string.strip()
    
    if not title:
        meta_title = soup.find("meta", {"name": "title"})
        if meta_title:
            title = meta_title.get("content", "").strip()
    
    if not title:
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title:
            title = og_title.get("content", "").strip()
    
    if not title:
        tw_title = soup.find("meta", {"property": "twitter:title"})
        if tw_title:
            title = tw_title.get("content", "").strip()
    
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)[:60]
    
    # Extract Meta Description
    meta_desc = ""
    meta_tag = soup.find("meta", {"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "").strip()
    
    if not meta_desc:
        meta_tag = soup.find("meta", {"property": "og:description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "").strip()
    
    if not meta_desc:
        meta_tag = soup.find("meta", {"property": "twitter:description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "").strip()
    
    if not meta_desc:
        meta_tag = soup.find("meta", {"itemprop": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "").strip()
    
    if not meta_desc:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                meta_desc = text[:160]
                break
    
    if not meta_desc:
        for tag in soup.find_all(["div", "section", "article"]):
            text = tag.get_text(strip=True)
            if text and len(text) > 20:
                meta_desc = text[:160]
                break
    
    # Extract keywords
    text_content = soup.get_text(" ", strip=True)
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text_content.lower())
    filtered_words = [w for w in words if w not in STOPWORDS]
    word_count = len(words)
    
    keyword_density = 0.0
    if filtered_words and word_count:
        counts = Counter(filtered_words)
        top_5_keywords = counts.most_common(5)
        top_counts = sum(count for _, count in top_5_keywords)
        keyword_density = round((top_counts / word_count) * 100, 2)
        print(f"Top keywords: {[f'{k}({c})' for k,c in top_5_keywords]}")
    
    return title, meta_desc, word_count, keyword_density

# Test both sites
sites = [
    "https://www.youtube.com",
    "https://bgsit.ac.in/",
]

for url in sites:
    print(f"\n{'='*70}")
    print(f"URL: {url}")
    print('='*70)
    try:
        title, meta_desc, word_count, kd = test_scraper(url)
        print(f"✅ Title: {title if title else 'NOT FOUND'}")
        print(f"✅ Meta Description: {meta_desc if meta_desc else 'NOT FOUND'}")
        print(f"✅ Word Count: {word_count}")
        print(f"✅ Keyword Density: {kd}%")
    except Exception as e:
        print(f"❌ ERROR: {e}")
