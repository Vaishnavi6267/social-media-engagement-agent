import os
import json
import logging
from typing import Dict, Any, List

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from backend.hindsight_client import HindsightMemoryService
except ImportError:
    from hindsight_client import HindsightMemoryService

logger = logging.getLogger("gemini_agent")
logger.setLevel(logging.INFO)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class SocialMediaEngagementAgent:
    """
    Social Media Engagement Agent powered by Google Gemini and Hindsight Memory.
    Drafts empathetic, brand-aligned responses grounded in past customer history, campaign knowledge, and brand guidelines.
    """

    def __init__(self, hindsight_service: HindsightMemoryService):
        self.hindsight = hindsight_service
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.client = None

        if self.api_key:
            if not GENAI_AVAILABLE:
                logger.warning("google-genai package not installed. Falling back to simulated engine.")
            else:
                try:
                    self.client = genai.Client(api_key=self.api_key)
                except Exception as e:
                    logger.warning(f"Could not initialize Gemini client: {e}")

    async def generate_draft_response(self, post: Dict[str, Any], include_hindsight: bool = True) -> Dict[str, Any]:
        """
        Drafts a response for an incoming post.
        If include_hindsight is True, pulls Hindsight memory reflection and cites sources.
        """
        content = post.get("content", "")
        author = post.get("author", "User")
        platform = post.get("platform", "Social Media")

        # 1. Retrieve Hindsight Memory
        reflection = {}
        recalled_memories = []
        if include_hindsight:
            reflection = await self.hindsight.reflect(
                query=f"How should we respond to {author} regarding {content} on {platform}?",
                context=json.dumps(post)
            )
            recalled_memories = reflection.get("recalled_memories", [])

        # Format memories for prompt
        memories_text = ""
        for idx, m in enumerate(recalled_memories, 1):
            memories_text += f"{idx}. [{m.get('type', 'fact')}] {m.get('content')}\n"

        if not memories_text:
            memories_text = "No prior memory records found for this specific query."

        # 2. Use Gemini if client available, otherwise high-quality mock engine grounded in prompt guidelines
        if self.client:
            try:
                system_prompt = (
                    "You are the Social Media Engagement Assistant for a leading brand. "
                    "Your goal is to draft professional, empathetic, brand-aligned responses to customer posts on social media.\n\n"
                    "RULES:\n"
                    "1. Never use flippant humor or snark when addressing customer complaints or delays.\n"
                    "2. Ground your suggested action in retrieved brand memory and guidelines if available.\n"
                    "3. If safety, legal, or extreme sensitivity is detected, explicitly flag for human escalation.\n"
                    "4. Always present a 'suggested_reply', 'reasoning', and 'citations'."
                )

                user_prompt = f"""
Incoming Post Details:
- Platform: {platform}
- Author: {author}
- Post Content: "{content}"

Retrieved Hindsight Memories:
{memories_text}

Hindsight Reflection Guidance:
{reflection.get('reasoning', 'N/A')}

Task:
Draft a suggested reply for the community manager. Explain your reasoning and cite which memory records (if any) informed your response. Return output as a JSON object with keys:
"suggested_reply", "reasoning", "citations", "flag_for_human_escalation" (boolean).
"""

                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    max_output_tokens=800,
                )

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=config,
                )

                text_out = response.text
                # Try parsing JSON
                try:
                    parsed = json.loads(text_out)
                    return {
                        "suggested_reply": parsed.get("suggested_reply"),
                        "reasoning": parsed.get("reasoning"),
                        "citations": parsed.get("citations", []),
                        "flag_for_human_escalation": parsed.get("flag_for_human_escalation", False),
                        "recalled_memories": recalled_memories,
                        "model_used": self.model
                    }
                except Exception:
                    return {
                        "suggested_reply": text_out,
                        "reasoning": reflection.get("reasoning", f"Generated by {self.model}"),
                        "citations": [m.get("content") for m in recalled_memories],
                        "flag_for_human_escalation": False,
                        "recalled_memories": recalled_memories,
                        "model_used": self.model
                    }

            except Exception as e:
                logger.warning(f"Gemini API call failed ({e}), using grounded fallback engine.")

        # 3. Grounded Fallback Engine (for demo execution without API keys)
        return self._generate_structured_fallback(post, recalled_memories, include_hindsight)

    def _generate_structured_fallback(self, post: Dict[str, Any], memories: List[Dict[str, Any]], include_hindsight: bool) -> Dict[str, Any]:
        content = post.get("content", "")
        author = post.get("author", "User")
        
        if not include_hindsight:
            # Generic response without Hindsight Memory
            return {
                "suggested_reply": f"Hi {author}, thanks for reaching out! We apologize for any inconvenience. Please reach out to our support team at support@example.com and we will look into this for you.",
                "reasoning": "Generic automated template applied without historical context or brand memory lookup.",
                "citations": [],
                "flag_for_human_escalation": False,
                "recalled_memories": [],
                "model_used": f"{self.model} (simulated)"
            }

        # Memory-Enhanced Fallback logic based on scenarios
        content_lower = content.lower()
        if "size" in content_lower or "sizing" in content_lower:
            reply = f"Hi {author}, we are so sorry about the sizing issue with your order! We recently updated our size guide graphic on our website to ensure perfect accuracy. We'd love to issue a free exchange right away—please send us a DM with your order number!"
            reasoning = "Hindsight recalled that during the 2025 launch, sizing confusion was resolved successfully by sharing the corrected size guide + free exchange offer. It also enforced the directive to avoid joke/flippant tones."
            citations = [m.get("content") for m in memories if "sizing" in m.get("content", "").lower() or "joke" in m.get("content", "").lower()]
        elif "deliver" in content_lower or "ship" in content_lower or "order #" in content_lower:
            reply = f"Hi {author}, thank you for checking in. We sincerely apologize for the delay on your order and the slow email response. We're prioritizing your order history directly with our fulfillment team now—sending you a DM shortly with an updated tracking link and resolution."
            reasoning = "Hindsight retrieved user history showing @alice_style previously experienced a delivery delay in March 2025 where a personal apology and DM follow-up resulted in a positive resolution."
            citations = [m.get("content") for m in memories if "alice" in m.get("content", "").lower() or "shipping" in m.get("content", "").lower()]
        elif "pricing" in content_lower or "bulk" in content_lower or "feature" in content_lower:
            reply = f"Hi {author}, thanks for the great question! Yes, v2 includes full bulk export capabilities for enterprise tier accounts. I'll drop a link to our updated pricing breakdown here: example.com/pricing-v2."
            reasoning = "Hindsight pulled knowledge base records regarding standard SLAs and campaign release details."
            citations = [m.get("content") for m in memories if "sla" in m.get("content", "").lower()]
        else:
            reply = f"Hi {author}, thanks for contacting us! We'd be happy to assist you with this. Please drop us a direct message so we can give this our full personal attention."
            reasoning = "Hindsight retrieved brand voice rules requiring an empathetic, helpful tone."
            citations = [m.get("content") for m in memories]

        return {
            "suggested_reply": reply,
            "reasoning": reasoning,
            "citations": citations if citations else ["Brand Voice Rule: Always maintain a helpful, empathetic tone."],
            "flag_for_human_escalation": False,
            "recalled_memories": memories,
            "model_used": f"{self.model} (simulated)"
        }
