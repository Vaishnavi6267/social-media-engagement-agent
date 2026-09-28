import os
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from backend.hindsight_client import HindsightMemoryService
    from backend.gemini_agent import SocialMediaEngagementAgent
except ImportError:
    from hindsight_client import HindsightMemoryService
    from gemini_agent import SocialMediaEngagementAgent

app = FastAPI(
    title="Social Media Engagement Agent powered by Hindsight Memory",
    description="API for multi-platform social media monitoring, Hindsight memory recall/reflection, and Gemini response drafting.",
    version="1.0.0"
)

# Initialize services
hindsight_service = HindsightMemoryService()
agent = SocialMediaEngagementAgent(hindsight_service=hindsight_service)

# Load sample posts
SAMPLE_POSTS_PATH = os.path.join(os.path.dirname(__file__), "sample_posts.json")
DATA_SAMPLE_POSTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_posts.json")

def load_posts() -> List[Dict[str, Any]]:
    target_path = SAMPLE_POSTS_PATH if os.path.exists(SAMPLE_POSTS_PATH) else DATA_SAMPLE_POSTS_PATH
    if os.path.exists(target_path):
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Models
class PostRequest(BaseModel):
    platform: str
    author: str
    content: str
    post_type: Optional[str] = "comment"

class MemoryCreateRequest(BaseModel):
    content: str
    memory_type: str = Field(default="observation", description="directive, observation, or experience")
    category: str = Field(default="general")

class DraftRequest(BaseModel):
    post: PostRequest
    include_hindsight: bool = True

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "Social Media Engagement Agent",
        "hindsight_memory": "active",
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "docs_url": "/docs"
    }

@app.get("/api/posts")
def get_posts():
    """Retrieve sample incoming social media posts for triage queue."""
    return {"posts": load_posts()}

@app.post("/api/draft")
async def generate_draft(req: DraftRequest):
    """Generate a response draft for a post using Google Gemini + Hindsight Memory."""
    post_dict = req.post.model_dump()
    result = await agent.generate_draft_response(post_dict, include_hindsight=req.include_hindsight)
    return result

@app.get("/api/scenario/before-after")
async def before_after_scenario(post_id: str = "post_001"):
    """
    Simulates the Before-and-After Scenario:
    Comparing generic/uncontextualized response vs. Hindsight Memory-Enhanced response.
    """
    posts = load_posts()
    post = next((p for p in posts if p.get("id") == post_id), posts[0] if posts else None)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    before_response = await agent.generate_draft_response(post, include_hindsight=False)
    after_response = await agent.generate_draft_response(post, include_hindsight=True)

    return {
        "post": post,
        "before": {
            "title": "Before (Without Hindsight Memory)",
            "time_to_resolve": "~4 Hours (Delayed & Generic)",
            "draft": before_response["suggested_reply"],
            "reasoning": before_response["reasoning"],
            "risk": "High risk of repetition of past mistakes, off-brand tone, and escalation."
        },
        "after": {
            "title": "After (With Hindsight Memory)",
            "time_to_resolve": "~20 Minutes (Instant Context)",
            "draft": after_response["suggested_reply"],
            "reasoning": after_response["reasoning"],
            "citations": after_response["citations"],
            "recalled_memories": after_response["recalled_memories"],
            "advantage": "Remembers past campaign resolution (size chart graphic + free exchange), avoids past tone mistake, and personalizes response."
        }
    }

@app.get("/api/memories")
def list_memories():
    """List all current retained memories in Hindsight memory bank."""
    return {"memories": hindsight_service.mock_memories}

@app.post("/api/memories")
async def add_memory(req: MemoryCreateRequest):
    """Add a new memory (rule, observation, experience) to Hindsight bank."""
    res = await hindsight_service.retain(content=req.content, memory_type=req.memory_type, category=req.category)
    return res

@app.get("/api/recall")
async def recall_memories(query: str = Query(..., description="Search query for memory bank")):
    """Run TEMPR 4-way search query against Hindsight Memory Bank."""
    results = await hindsight_service.recall(query=query)
    return {"query": query, "results": results}
