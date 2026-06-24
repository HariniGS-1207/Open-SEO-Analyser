import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

sites = [
    "https://www.youtube.com",
    "https://bgsit.ac.in/",
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for url in sites:
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print('='*60)
    
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False, allow_redirects=True)
        print(f"Status: {r.status_code}")
        print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
        print(f"HTML Length: {len(r.text)} characters")
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Check for title
        title = soup.title.string if soup.title else None
        print(f"Title: {title}")
        
        # Check for meta description
        meta_desc = soup.find("meta", {"name": "description"})
        print(f"Meta Description: {meta_desc.get('content') if meta_desc else 'NOT FOUND'}")
        
        # Check for og:description
        og_desc = soup.find("meta", {"property": "og:description"})
        print(f"OG Description: {og_desc.get('content') if og_desc else 'NOT FOUND'}")
        
        # Show first 500 chars
        print(f"\nFirst 500 chars of HTML:")
        print(r.text[:500])
        print("\n...")
        
    except Exception as e:
        print(f"ERROR: {e}")
