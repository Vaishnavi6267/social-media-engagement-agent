import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger("hindsight_service")
logger.setLevel(logging.INFO)

HINDSIGHT_API_URL = os.getenv("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "")
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "social-media-engagement-agent")

class HindsightMemoryService:
    """
    Client for Hindsight Memory API (retain, recall, reflect, mental_models).
    Includes a built-in mock fallback for standalone demo execution.
    """

    def __init__(self, api_url: str = HINDSIGHT_API_URL, api_key: str = HINDSIGHT_API_KEY, bank_id: str = BANK_ID):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.bank_id = bank_id
        self.use_mock = not bool(self.api_key)
        self.mock_memories: List[Dict[str, Any]] = []
        self._load_seed_data()

    def _load_seed_data(self):
        seed_path = os.path.join(os.path.dirname(__file__), "..", "data", "seed_memories.json")
        if os.path.exists(seed_path):
            try:
                with open(seed_path, "r", encoding="utf-8") as f:
                    self.mock_memories = json.load(f)
            except Exception as e:
                logger.error(f"Error loading seed memories: {e}")

    async def retain(self, content: str, memory_type: str = "observation", category: str = "general") -> Dict[str, Any]:
        """Store information in Hindsight memory bank."""
        item = {
            "content": content,
            "type": memory_type,
            "category": category,
            "timestamp": "2026-03-31T12:00:00Z"
        }
        self.mock_memories.append(item)

        if not self.use_mock:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "bank_id": self.bank_id,
                "memories": [{"type": memory_type, "content": content, "metadata": {"category": category}}]
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{self.api_url}/v1/retain", json=payload, headers=headers)
                    if resp.status_code == 200:
                        return resp.json()
            except Exception as e:
                logger.warning(f"Hindsight API retain call failed, falling back to mock: {e}")

        return {"status": "success", "message": "Retained in memory bank", "item": item, "is_mock": self.use_mock}

    async def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Multi-strategy search across memory bank."""
        if not self.use_mock:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {"bank_id": self.bank_id, "query": query, "limit": limit}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{self.api_url}/v1/recall", json=payload, headers=headers)
                    if resp.status_code == 200:
                        return resp.json().get("results", [])
            except Exception as e:
                logger.warning(f"Hindsight API recall failed, falling back to mock: {e}")

        # Local mock matching heuristic
        query_words = set(query.lower().split())
        matched = []
        for mem in self.mock_memories:
            content_lower = mem["content"].lower()
            overlap = sum(1 for word in query_words if word in content_lower)
            if overlap > 0 or "rule" in query_words or "size" in content_lower:
                matched.append({
                    "content": mem["content"],
                    "type": mem.get("type", "observation"),
                    "category": mem.get("category", "general"),
                    "relevance_score": min(0.95, 0.6 + (overlap * 0.1))
                })

        if not matched:
            matched = [{"content": m["content"], "type": m.get("type"), "category": m.get("category"), "relevance_score": 0.7} for m in self.mock_memories[:limit]]

        return matched[:limit]

    async def reflect(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Agentic reasoning using Hindsight Mission, Directives, and Memory Banks."""
        recalled = await self.recall(query)

        if not self.use_mock:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {"bank_id": self.bank_id, "query": query, "context": context}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{self.api_url}/v1/reflect", json=payload, headers=headers)
                    if resp.status_code == 200:
                        return resp.json()
            except Exception as e:
                logger.warning(f"Hindsight API reflect failed, falling back to mock: {e}")

        # Synthesized reasoning based on recalled memories
        reasoning_points = []
        for r in recalled:
            reasoning_points.append(f"- Derived from [{r.get('type', 'fact')}]: {r.get('content')}")

        reasoning_summary = "\n".join(reasoning_points) if reasoning_points else "- Checked core brand guidelines & campaign history."

        return {
            "bank_id": self.bank_id,
            "query": query,
            "recalled_memories": recalled,
            "reasoning": f"Hindsight Memory Reflection:\n{reasoning_summary}\n\nDisposition applied: Empathetic, careful, grounded in prior successful resolutions.",
            "is_mock": self.use_mock
        }

    def list_all_memories(self) -> List[Dict[str, Any]]:
        return self.mock_memories
