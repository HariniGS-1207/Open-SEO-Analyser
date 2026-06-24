import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

url = "https://bgsit.ac.in/"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

try:
    r = requests.get(url, headers=headers, timeout=15, verify=False, allow_redirects=True)
    print(f"Status: {r.status_code}")
    print(f"URL: {r.url}")
    
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Extract Title - try multiple methods
    title = ""
    title_tag = soup.title
    if title_tag and title_tag.string:
        title = title_tag.string.strip()
    
    # Fallback: check for meta name="title"
    if not title:
        meta_title = soup.find("meta", {"name": "title"})
        if meta_title:
            title = meta_title.get("content", "").strip()
    
    # Fallback: check og:title
    if not title:
        og_title = soup.find("meta", {"property": "og:title"})
        if og_title:
            title = og_title.get("content", "").strip()
    
    print(f"\nTitle: {title}")
    
    # Extract Meta Description
    meta_desc = ""
    meta_tag = soup.find("meta", {"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "").strip()
    
    # Fallback: check other description sources
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
    
    # Fallback: extract first paragraph as description if no meta exists
    if not meta_desc:
        p_tag = soup.find("p")
        if p_tag:
            meta_desc = p_tag.get_text(strip=True)[:160]
    
    print(f"Meta Description: {meta_desc}")
    print(f"\n✅ Both title and meta extracted!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
