"""
FastAPI web app for Regulatory Intelligence admin panel.

Serves HTML templates with HTMX for interactivity.

Usage:
    uvicorn api.main:app --reload --port 8000
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.db_client import DBClient

# Setup templates
API_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=API_DIR / "templates")

# Global DB client
db: DBClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    db = DBClient(auto_sync=True)
    yield


app = FastAPI(
    title="Regulatory Intelligence Admin",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory=API_DIR / "static"), name="static")


# ==================== HTML Pages ====================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Home page - redirects to users."""
    return RedirectResponse(url="/users", status_code=302)


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    """Users management page."""
    users = db.get_all_users(active_only=False)
    users_data = []
    for u in users:
        topics = db.get_user_topics(u.user_id)
        users_data.append({
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "is_active": u.is_active,
            "subscribed_topics": [t.topic_name for t in topics],
        })
    all_topics = db.get_all_topics()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users_data,
        "topics": all_topics,
        "active_page": "users",
    })


@app.post("/users/add", response_class=HTMLResponse)
def add_user(request: Request, name: str = Form(...), email: str = Form(...), topics: list = Form(default=[])):
    """Add a new user."""
    with db.connection() as conn:
        cursor = conn.execute("SELECT user_id FROM Users WHERE email = ?", (email,))
        if cursor.fetchone():
            return RedirectResponse(url="/users?error=Email+already+exists", status_code=302)
        
        cursor = conn.execute(
            "INSERT INTO Users (name, email) VALUES (?, ?) RETURNING user_id",
            (name, email)
        )
        user_id = cursor.fetchone()[0]
        
        # Add topic subscriptions
        for topic_id in topics:
            conn.execute(
                "INSERT INTO User_Topics (user_id, topic_id) VALUES (?, ?)",
                (user_id, int(topic_id))
            )
    
    db.upload_to_gcs()
    return RedirectResponse(url="/users", status_code=302)


@app.post("/users/{user_id}/delete", response_class=HTMLResponse)
def delete_user_page(user_id: int):
    """Delete a user."""
    with db.connection() as conn:
        conn.execute("DELETE FROM User_Topics WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
    db.upload_to_gcs()
    return RedirectResponse(url="/users", status_code=302)


@app.get("/topics", response_class=HTMLResponse)
def topics_page(request: Request):
    """Topics management page."""
    topics = db.get_all_topics()
    topics_data = []
    for t in topics:
        sources = db.get_sources_by_topic_id(t.topic_id)
        topics_data.append({
            "topic_id": t.topic_id,
            "topic_name": t.topic_name,
            "source_count": len(sources),
        })
    return templates.TemplateResponse("topics.html", {
        "request": request,
        "topics": topics_data,
        "active_page": "topics",
    })


@app.post("/topics/add", response_class=HTMLResponse)
def add_topic(request: Request, topic_name: str = Form(...)):
    """Add a new topic."""
    existing = db.get_topic_by_name(topic_name)
    if existing:
        return RedirectResponse(url="/topics?error=Topic+already+exists", status_code=302)
    
    db.add_topic(topic_name)
    db.upload_to_gcs()
    return RedirectResponse(url="/topics", status_code=302)


@app.post("/topics/{topic_id}/delete", response_class=HTMLResponse)
def delete_topic_page(topic_id: int):
    """Delete a topic."""
    with db.connection() as conn:
        conn.execute("DELETE FROM Source_Topics WHERE topic_id = ?", (topic_id,))
        conn.execute("DELETE FROM User_Topics WHERE topic_id = ?", (topic_id,))
        conn.execute("DELETE FROM Topics WHERE topic_id = ?", (topic_id,))
    db.upload_to_gcs()
    return RedirectResponse(url="/topics", status_code=302)


@app.get("/sources", response_class=HTMLResponse)
def sources_page(request: Request):
    """Sources management page."""
    sources = db.get_all_sources(active_only=False)
    topics = db.get_all_topics()
    countries = db.get_all_countries()
    return templates.TemplateResponse("sources.html", {
        "request": request,
        "sources": sources,
        "topics": topics,
        "countries": countries,
        "active_page": "sources",
    })


@app.post("/sources/add", response_class=HTMLResponse)
def add_source(
    request: Request,
    source_name: str = Form(...),
    feed_url: str = Form(...),
    country_code: str = Form(default="US"),
    topics: list = Form(default=[]),
):
    """Add a new source."""
    topic_ids = [int(t) for t in topics] if topics else []
    db.add_source(
        source_name=source_name,
        inoreader_stream_id="",
        feed_url=feed_url,
        country_code=country_code,
        topic_ids=topic_ids,
    )
    db.upload_to_gcs()
    return RedirectResponse(url="/sources", status_code=302)


@app.post("/sources/{source_id}/delete", response_class=HTMLResponse)
def delete_source_page(source_id: int):
    """Delete a source."""
    with db.connection() as conn:
        conn.execute("DELETE FROM Source_Topics WHERE source_id = ?", (source_id,))
        conn.execute("DELETE FROM Sources WHERE source_id = ?", (source_id,))
    db.upload_to_gcs()
    return RedirectResponse(url="/sources", status_code=302)


# ==================== API Endpoints ====================

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    stats = db.get_stats()
    return {"status": "healthy", "stats": stats}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
