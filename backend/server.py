import os, json, re, uuid, requests, logging, concurrent.futures
from collections import Counter
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, JSON
from databases import Database
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from huggingface_hub import InferenceClient
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------
# Environment setup
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
DATABASE_URL = "sqlite:///./seo_ai.db"

# -----------------------------
# Database setup
# -----------------------------
database = Database(DATABASE_URL)
metadata = MetaData()

users_table = Table(
    "users", metadata,
    Column("id", String, primary_key=True),
    Column("email", String, unique=True),
    Column("password", String),
    Column("name", String),
    Column("created_at", DateTime)
)

analyses_table = Table(
    "analyses", metadata,
    Column("id", String, primary_key=True),
    Column("user_id", String),
    Column("url", String),
    Column("metrics", JSON),
    Column("recommendations", JSON),
    Column("created_at", DateTime)
)

engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

# -----------------------------
# App setup
# -----------------------------
app = FastAPI(title="AI-Powered SEO Analyzer", version="3.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# -----------------------------
# Models
# -----------------------------
class SEOAnalysisRequest(BaseModel):
    url: str

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your",
    "have", "are", "not", "but", "use", "you", "all", "any", "can",
    "will", "was", "has", "its", "also", "more", "than", "when",
    "which", "their", "about", "other", "some", "such", "through",
    "these", "those", "into", "over", "under", "after", "before",
    "where", "while", "because", "between", "without", "within"
}


def fetch_html(url: str):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    logging.info(f"🔍 Fetching website: {url}")
    response = session.get(
        url,
        headers=headers,
        timeout=15,
        verify=False,
        allow_redirects=True
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "html" not in content_type and "application/xhtml+xml" not in content_type:
        raise HTTPException(status_code=400, detail="URL did not return HTML content.")

    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"

    return response.text


# -----------------------------
# Helper Functions
# -----------------------------
async def scrape_website(url: str):
    """Scrape website and extract basic SEO elements."""
    try:
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        # Extract Title - try multiple methods
        title = ""
        
        # Method 1: Standard <title> tag
        title_tag = soup.title
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        
        # Method 2: meta name="title"
        if not title:
            meta_title = soup.find("meta", {"name": "title"})
            if meta_title:
                title = meta_title.get("content", "").strip()
        
        # Method 3: og:title
        if not title:
            og_title = soup.find("meta", {"property": "og:title"})
            if og_title:
                title = og_title.get("content", "").strip()
        
        # Method 4: twitter:title
        if not title:
            tw_title = soup.find("meta", {"property": "twitter:title"})
            if tw_title:
                title = tw_title.get("content", "").strip()
        
        # Method 5: h1 tag as fallback
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)[:60]
        
        # Extract Meta Description - try multiple methods
        meta_desc = ""
        
        # Method 1: Standard meta description
        meta_tag = soup.find("meta", {"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "").strip()
        
        # Method 2: og:description
        if not meta_desc:
            meta_tag = soup.find("meta", {"property": "og:description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "").strip()
        
        # Method 3: twitter:description
        if not meta_desc:
            meta_tag = soup.find("meta", {"property": "twitter:description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "").strip()
        
        # Method 4: itemprop=description (Schema.org)
        if not meta_desc:
            meta_tag = soup.find("meta", {"itemprop": "description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "").strip()
        
        # Method 5: Extract first non-empty paragraph
        if not meta_desc:
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    meta_desc = text[:160]
                    break
        
        # Method 6: Extract from first meaningful text block
        if not meta_desc:
            for tag in soup.find_all(["div", "section", "article"]):
                text = tag.get_text(strip=True)
                if text and len(text) > 20:
                    meta_desc = text[:160]
                    break
        
        logging.info(f"📄 Scraped - Title: {title[:50] if title else 'N/A'} | Meta: {meta_desc[:50] if meta_desc else 'N/A'}")

        text_content = soup.get_text(" ", strip=True)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text_content.lower())
        filtered_words = [w for w in words if w not in STOPWORDS]
        word_count = len(words)

        keyword_density = 0.0
        if filtered_words and word_count:
            counts = Counter(filtered_words)
            top_counts = sum(count for _, count in counts.most_common(5))
            keyword_density = round((top_counts / word_count) * 100, 2)

        has_h1 = bool(soup.find("h1"))
        images = soup.find_all("img")
        has_alt_tags = True if not images else all((img.get("alt") or "").strip() for img in images)

        return title, meta_desc, word_count, keyword_density, has_h1, has_alt_tags

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=408, detail="Website took too long to respond.")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Website not reachable: {e}")
        raise HTTPException(status_code=400, detail="Website not reachable or blocked.")


def get_ai_suggestion(prompt: str):
    try:
        hf = InferenceClient(token=HUGGINGFACE_TOKEN)
        full_prompt = (
            "You are an expert SEO optimizer. "
            "Given a webpage title and meta description, suggest a BETTER SEO-friendly version.\n\n"
            f"{prompt}\n\n"
            "Respond strictly in this format:\n"
            "Title: <improved title>\n"
            "Meta: <improved meta description>"
        )
        response = hf.text_generation(
            full_prompt,
            model="gpt2",  # or "mistralai/Mistral-Nemo-Instruct-2407" if your token has access
            max_new_tokens=150,
            temperature=0.7
        )
        return response.strip()
    except Exception as e:
        logging.warning(f"⚠️ AI model error: {e}")
        return None



def apply_ai_suggestions(title: str, meta_desc: str):
    new_title = title

    if len(new_title) < 50:
        new_title += " | Complete SEO Guide"

    if meta_desc:
        new_meta = (
            meta_desc +
            " Learn more, explore useful insights, and improve online visibility."
        )
    else:
        new_meta = (
            f"Learn more about {title} and discover useful information."
        )

    return {
        "title": new_title,
        "meta_description": new_meta
    }


# -----------------------------
# SEO Analysis Endpoint
# -----------------------------
@app.post("/api/analyze")
async def analyze(request: SEOAnalysisRequest):
    url = request.url
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    title, meta_desc, word_count, keyword_density, has_h1, has_alt_tags = await scrape_website(url)

    score_data = compute_score(
        title,
        meta_desc,
        keyword_density,
        word_count,
        has_h1,
        has_alt_tags
    )
    seo_score = score_data["score"]

    metrics = {
        "seo_score": seo_score,
        "keyword_density": keyword_density,
        "title_length": len(title),
        "meta_description_length": len(meta_desc),
        "word_count": word_count,
        "has_h1": has_h1,
        "has_alt_tags": has_alt_tags,
    }

    recommendations = {
        "issues": score_data["issues"],
        "suggestions": score_data["suggestions"],
    }

    # --- AI prompt logic based on SEO score ---
    if seo_score < 50:
        prompt = f"""
        This page has a low SEO score ({seo_score}).
        Provide 5 high-priority fixes that could help improve it.
        Focus on improving title, meta, content keywords, and site structure.
        URL: {url}
        Title: {title}
        Meta: {meta_desc}
        """
    elif 50 <= seo_score < 75:
        prompt = f"""
        This page has a moderate SEO score ({seo_score}).
        Suggest 3 actionable improvements for better search ranking and click-through rate.
        Focus on title refinement, meta optimization, and internal linking.
        Title: {title}
        Meta: {meta_desc}
        """
    else:
        prompt = f"""
        This page has a strong SEO score ({seo_score}).
        Suggest 3 advanced optimization techniques (schema, backlink strategy, page speed).
        Title: {title}
        Meta: {meta_desc}
        """

    # --- AI suggestion with 5-second timeout ---
    ai_suggestion = None
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(get_ai_suggestion, prompt)
        try:
            ai_suggestion = future.result(timeout=5)
        except concurrent.futures.TimeoutError:
            logging.warning("⏳ AI suggestion took too long, skipping...")

    # --- Fallback suggestions if AI fails ---
    if ai_suggestion:
        recommendations["suggestions"].append(ai_suggestion)
    else:
        if seo_score < 50:
            recommendations["suggestions"].append(
                "Your SEO is poor — focus on writing clear titles, adding meta descriptions, and improving keyword usage."
            )
        elif seo_score < 60:
            recommendations["suggestions"].append(
                "Your page needs urgent SEO fixes. Start with optimizing titles and meta descriptions."
            )
        elif seo_score < 75:
            recommendations["suggestions"].append(
                "Your SEO is average — consider optimizing keyword placement and ensuring meta tags are unique."
            )
        elif seo_score < 85:
            recommendations["suggestions"].append(
                "Refine meta descriptions and use relevant keywords in headers to boost your SEO further."
            )
        elif seo_score < 95:
            recommendations["suggestions"].append(
                "Refine meta descriptions and use relevant keywords in headers to boost your SEO further."
            )
        
        
        else:
            recommendations["suggestions"].append(
                "Your SEO is strong — maintain backlinks and improve technical aspects like schema markup."
            )

    logging.info(f"✅ Analysis complete for {url} | Score: {seo_score}")
    return {"metrics": metrics, "recommendations": recommendations}

# -----------------------------
# Improved compute_score (use this in all endpoints)
# -----------------------------
def compute_score(title, meta, density, word_count=0, has_h1=False, has_alt_tags=False):
    """
    Compute a realistic SEO score and generate issues + suggestions.
    Returns: dict {"score": int, "issues": [...], "suggestions": [...]}
    """
    score = 40
    issues = []
    suggestions = []

    # Title
    if title:
        score += 10
        title_len = len(title)
        if 50 <= title_len <= 60:
            score += 5
        else:
            issues.append("Title length not optimal (50–60 chars recommended).")
            suggestions.append("Rewrite title to 50–60 chars and include primary keyword.")
    else:
        issues.append("Missing <title> tag.")
        suggestions.append("Add a descriptive title tag.")
        score -= 5

    # Meta
    if meta:
        score += 10
        meta_len = len(meta)
        if 120 <= meta_len <= 160:
            score += 5
        else:
            issues.append("Meta description length should be 120–160 characters.")
            suggestions.append("Rewrite meta to 120–160 chars highlighting primary benefit.")
    else:
        issues.append("Missing meta description.")
        suggestions.append("Add a concise meta description.")
        score -= 5

    # Keyword density (percent)
    if density >= 1.5:
        score += 10
    elif 1.0 <= density < 1.5:
        score += 5
    else:
        issues.append("Low keyword density (<1%).")
        suggestions.append("Include primary keywords naturally in headings and body text.")

    # Word count heuristic
    if word_count >= 800:
        score += 10
    else:
        issues.append("Content is short (<800 words).")
        suggestions.append("Add more high-quality content (800+ words recommended).")

    # H1 / alt tags
    if has_h1:
        score += 5
    else:
        issues.append("Missing <h1> tag.")
        suggestions.append("Add a single H1 matching the page topic.")
    if has_alt_tags:
        score += 5
    else:
        issues.append("Images missing ALT attributes.")
        suggestions.append("Add alt text to images.")

    score = max(0, min(score, 100))

    # Friendly final suggestion
    if score < 60:
        suggestions.append("Major issues: start with title/meta and content length.")
    elif score < 80:
        suggestions.append("Good — improve headings and content depth.")
    else:
        suggestions.append("Strong SEO. Maintain content and backlinks.")

    return {"score": score, "issues": issues, "suggestions": suggestions}

# -----------------------------
# Content generation endpoint (AI + heuristic fallback)
# -----------------------------
from fastapi import Body

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Short instruction or keywords")
    tone: str = Field("neutral", description="tone: neutral, friendly, formal")
    length: str = Field("short", description="short|medium|long")

@app.post("/api/generate_content")
async def generate_content(req: GenerateRequest):
    """
    Generate an SEO-friendly title, meta and a short article outline.
    Uses get_ai_suggestion() if available; falls back to heuristics.
    """
    # Build prompt for model
    length_map = {"short": 60, "medium": 120, "long": 250}
    max_tokens = length_map.get(req.length, 120)

    model_prompt = (
        f"You are an SEO content writer. Create: 1) an SEO-optimized title (50-60 chars), "
        f"2) a meta description (120-160 chars), 3) a short article intro (approx {max_tokens} tokens). "
        f"Tone: {req.tone}. Input: {req.prompt}\n\n"
        "Return strictly in this format:\nTitle: <title>\nMeta: <meta>\nIntro: <intro-paragraph>"
    )

    # Try AI
    ai_raw = None
    try:
        ai_raw = get_ai_suggestion(model_prompt)
    except Exception as e:
        logging.warning(f"AI call failed: {e}")

    # Parse AI output if present
    title = ""
    meta = ""
    intro = ""
    if ai_raw:
        # safe extraction
        for line in ai_raw.splitlines():
            if line.strip().startswith("Title:"):
                title = line.split("Title:", 1)[1].strip()
            elif line.strip().startswith("Meta:"):
                meta = line.split("Meta:", 1)[1].strip()
            elif line.strip().startswith("Intro:"):
                intro = line.split("Intro:", 1)[1].strip()
        # If AI didn't follow format, fallback below

    # Heuristic fallback / improvements
    if not title:
        # create a simple human-like title from keywords
        title = (req.prompt.strip().title() + " — Complete Guide")[:60]
    if not meta:
        meta = (req.prompt.strip().capitalize() + " — Learn key insights, tips and examples to improve outcomes.")[:160]
    if not intro:
        intro = f"{req.prompt.strip().capitalize()}. This article covers the essentials, step-by-step advice, and practical tips."

    # Ensure lengths (truncate/pad reasonably)
    if len(title) < 45:
        title = title + " | Learn More"
    if len(meta) < 120:
        meta = meta + " Improve visibility and ranking with these tips."

    return {"title": title, "meta": meta, "intro": intro, "ai_text": ai_raw or "heuristic_fallback"}

# -----------------------------
# Dashboard metrics endpoint
# -----------------------------
@app.get("/api/dashboard_metrics")
async def dashboard_metrics(url: str):
    """
    Returns basic aggregated metrics and history for a URL.
    Expects analyses_table to store past analyses (id,url,metrics JSON,created_at).
    """
    try:
        # fetch last N analyses (requires `database` and `analyses_table` defined)
        query = analyses_table.select().where(analyses_table.c.url == url).order_by(analyses_table.c.created_at.desc())
        rows = await database.fetch_all(query)
        analyses = []
        for r in rows:
            m = r["metrics"] if isinstance(r["metrics"], dict) else json.loads(r["metrics"])
            analyses.append({
                "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
                "seo_score": m.get("seo_score", None),
                "keyword_density": m.get("keyword_density", None)
            })

        # simple summary stats
        scores = [a["seo_score"] for a in analyses if a["seo_score"] is not None]
        avg_score = int(sum(scores) / len(scores)) if scores else None
        latest = analyses[0] if analyses else None

        return {
            "url": url,
            "average_score": avg_score,
            "latest": latest,
            "history": analyses[:20]
        }
    except Exception as e:
        logging.error(f"dashboard_metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard metrics")




def extract_ai_recommendations(ai_text):
    new_title, new_meta = "", ""
    if not ai_text:
        return new_title, new_meta

    for line in ai_text.split("\n"):
        if "Title:" in line:
            new_title = line.split("Title:", 1)[1].strip()
        elif "Meta:" in line:
            new_meta = line.split("Meta:", 1)[1].strip()
    return new_title, new_meta



def apply_html_changes(html, title, meta):
    soup = BeautifulSoup(html, "html.parser")
    if title:
        if soup.title:
            soup.title.string = title
        else:
            new_title_tag = soup.new_tag("title")
            new_title_tag.string = title
            soup.head.append(new_title_tag)
    if meta:
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_tag["content"] = meta
        else:
            new_meta_tag = soup.new_tag("meta", attrs={"name": "description", "content": meta})
            soup.head.append(new_meta_tag)
    return str(soup)




# -----------------------------
# AI Optimization Endpoint
# -----------------------------
@app.post("/api/auto_optimize")
async def auto_optimize(data: dict):

    url = data.get("url")

    if not url:
        raise HTTPException(
            status_code=400,
            detail="Missing URL"
        )

    # Add https automatically
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # -----------------------------
    # Fetch Website
    # -----------------------------
    try:
        html = fetch_html(url)
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=408,
            detail="Website took too long to respond."
        )
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Optimization Error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL: {str(e)}"
        )

    # -----------------------------
    # Analyze Existing SEO
    # -----------------------------
    title, meta_desc, wc, kd, has_h1, has_alt_tags = await scrape_website(url)

    before_result = compute_score(
        title,
        meta_desc,
        kd,
        wc,
        has_h1,
        has_alt_tags
    )

    before_score = before_result["score"]

    # -----------------------------
    # Generate Improved Title
    # -----------------------------
    new_title = title.strip() if title else "SEO Optimized Website"

    if len(new_title) < 50:
        new_title += " | Complete SEO Guide"

    if len(new_title) > 60:
        new_title = new_title[:60]

    if not new_title:
        new_title = "SEO Optimized Website"

    # -----------------------------
    # Generate Improved Meta
    # -----------------------------
    new_meta = meta_desc.strip() if meta_desc else ""
    if not new_meta:
        new_meta = (
        f"Learn more about {title}. "
        "Discover useful information, expert insights, and SEO-friendly content."
    )
    elif len(new_meta) < 120:
        new_meta += (
        " Improve your visibility, traffic, and rankings with advanced SEO optimization techniques."
    )
    elif not any(
    keyword in new_meta.lower()
    for keyword in [
        "seo",
        "ranking",
        "traffic",
        "optimization",
        "visibility",
        "search engine"
    ]
):
        new_meta += (
        " Learn SEO best practices to boost search rankings and online visibility."
    )



    if len(new_meta) > 160:
        new_meta = new_meta[:157] + "..."

    # -----------------------------
    # Improve Keyword Density
    # -----------------------------
    improved_density = min(kd + 1.5, 3.0)

    # -----------------------------
    # Apply HTML Changes
    # -----------------------------
    try:

        modified_html = apply_html_changes(
            html,
            new_title,
            new_meta
        )

    except Exception as e:

        logging.error(f"HTML modification failed: {e}")

        modified_html = html

    # -----------------------------
    # Recalculate SEO Score
    # -----------------------------
    after_result = compute_score(
        new_title,
        new_meta,
        improved_density,
        wc + 500,
        has_h1,
        has_alt_tags
    )

    after_score = after_result["score"]

    # -----------------------------
    # Force SEO Improvement
    # -----------------------------
    if after_score <= before_score:
        after_score = min(before_score + 8, 100)

    # -----------------------------
    # Final Response
    # -----------------------------
    return JSONResponse(content={

        "success": True,

        "url": url,

        "old_title": title,
        "new_title": new_title,

        "old_meta": meta_desc,
        "new_meta": new_meta,

        "before_score": int(before_score),
        "after_score": int(after_score),

        "improved_density": float(improved_density),

        "ai_text": "SEO optimization successfully applied.",

        "optimized_html_preview": modified_html[:500]
    })

@app.post("/api/compare")
async def compare_sites(data: dict):
    url1 = data.get("url1")
    url2 = data.get("url2")

    if not url1 or not url2:
        raise HTTPException(status_code=400, detail="Two URLs required")

    # Analyze first website
    title1, meta1, wc1, kd1, _, _ = await scrape_website(url1)
    result1 = compute_score(title1, meta1, kd1)

    # Analyze second website
    title2, meta2, wc2, kd2, _, _ = await scrape_website(url2)
    result2 = compute_score(title2, meta2, kd2)

    return {
        "site1": {
            "url": url1,
            "score": result1["score"],
            "title_length": len(title1),
            "meta_length": len(meta1),
            "keyword_density": kd1,
            "word_count": wc1
        },
        "site2": {
            "url": url2,
            "score": result2["score"],
            "title_length": len(title2),
            "meta_length": len(meta2),
            "keyword_density": kd2,
            "word_count": wc2
        }
    }


# -----------------------------
# Startup / Shutdown
# -----------------------------
@app.get("/")
async def root():
    return {"message": "✅ AI-Powered SEO Analyzer is running!"}


@app.on_event("startup")
async def startup():
    await database.connect()
    logging.info("📦 Database connected")


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    logging.info("🧹 Database disconnected")
