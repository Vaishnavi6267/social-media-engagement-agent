import gradio as gr
import asyncio
import os
import sys

# Ensure backend imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.main import load_posts, hindsight_service, agent
except ImportError:
    from main import load_posts, hindsight_service, agent

def respond_to_post(platform, author, content, use_hindsight):
    post = {
        "platform": platform,
        "author": author,
        "content": content
    }
    
    res = asyncio.run(agent.generate_draft_response(post, include_hindsight=use_hindsight))
    
    citations_str = "\n".join([f"- 📌 {c}" for c in res.get("citations", [])]) if res.get("citations") else "No direct citations retrieved."
    
    output_md = f"""### 🤖 Suggested Reply:
> {res['suggested_reply']}

---
### 🧠 Hindsight Reasoning:
{res['reasoning']}

---
### 📚 Citations & Evidence:
{citations_str}
"""
    return output_md

def search_hindsight(query):
    if not query:
        return "Please enter a search query."
    results = asyncio.run(hindsight_service.recall(query))
    out = f"### 🔍 TEMPR Search Results for: '{query}'\n\n"
    for r in results:
        out += f"- **[{r.get('type', 'fact').upper()}]** ({r.get('category', 'general')}): {r.get('content')}\n"
    return out

def add_memory_item(content, memory_type, category):
    if not content:
        return "Memory content cannot be empty."
    asyncio.run(hindsight_service.retain(content, memory_type=memory_type, category=category))
    return f"✅ Successfully retained memory: [{memory_type}] {content}"

# Create Gradio Blocks Interface
with gr.Blocks(title="Social Media Engagement Agent | Gradio Demo") as demo:
    gr.Markdown("# 🧠 Social Media Engagement Agent (Powered by Hindsight)")
    gr.Markdown("Lightweight interactive interface for quick testing and judge evaluation.")
    
    with gr.Tab("💬 Interactive Post Triaging"):
        gr.Markdown("### Draft a response for any custom or sample post using Hindsight Agent Memory")
        
        with gr.Row():
            with gr.Column():
                platform_in = gr.Dropdown(choices=["Instagram", "X (Twitter)", "LinkedIn", "Facebook"], value="Instagram", label="Platform")
                author_in = gr.Textbox(value="@fashion_influencer_22", label="Author Handle")
                content_in = gr.Textbox(
                    value="Hey! The new product line sizing chart on your site is completely wrong. Order #8821 arrived and medium is way too small. Is anyone checking this?",
                    label="Post Content",
                    lines=3
                )
                use_hindsight_chk = gr.Checkbox(value=True, label="Enable Hindsight Memory Recall & Reflection")
                submit_btn = gr.Button("Draft Response", variant="primary")
            
            with gr.Column():
                output_box = gr.Markdown(label="Agent Response & Reasoning")
                
        submit_btn.click(
            fn=respond_to_post,
            inputs=[platform_in, author_in, content_in, use_hindsight_chk],
            outputs=[output_box]
        )

    with gr.Tab("🔍 Memory Bank Search & Add"):
        gr.Markdown("### Search TEMPR Memory Bank & Add Brand Rules")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Search Memories")
                search_query = gr.Textbox(label="Query", placeholder="e.g. sizing, late delivery, brand rules...")
                search_btn = gr.Button("Search Memory")
                search_output = gr.Markdown()
                search_btn.click(fn=search_hindsight, inputs=[search_query], outputs=[search_output])
                
            with gr.Column():
                gr.Markdown("#### Retain New Memory")
                mem_type = gr.Dropdown(choices=["directive", "observation", "experience"], value="observation", label="Type")
                mem_cat = gr.Dropdown(choices=["brand_rule", "campaign_history", "past_mistakes", "user_history", "knowledge_base"], value="brand_rule", label="Category")
                mem_text = gr.Textbox(label="Fact / Rule Content", lines=2)
                add_btn = gr.Button("Retain Memory", variant="primary")
                add_output = gr.Textbox(label="Status")
                add_btn.click(fn=add_memory_item, inputs=[mem_text, mem_type, mem_cat], outputs=[add_output])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
