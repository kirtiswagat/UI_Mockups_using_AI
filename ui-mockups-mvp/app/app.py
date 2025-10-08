# app/app.py
import os, io, time, json, base64
from pathlib import Path
from typing import Dict, Any, List

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from utils.file_readers import read_file_text

# ---------- Load .env from repo root (works no matter where Streamlit is launched) ----------
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("WARN: OPENAI_API_KEY missing. Set it in .env at repo root.")
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- UI: Page config ----------
st.set_page_config(page_title="UI Mockups (MVP+ Planner)", page_icon="🎨", layout="wide")
st.title("🎨 UI Mockups — Planner → Generate → Verify (MVP+)")

# ============================================================================================
# Prompt builder utilities (planner + per-screen image prompt)
# ============================================================================================
PLANNER_SYSTEM = """You are a senior product designer. Extract a precise UI plan from user requirements.
Return ONLY JSON with keys:
- screens: array of objects {name, goal, must, layout, components, tone, color, density}
- global_style: {tone, color, density, typography}
Be specific. Keep 'must' as short imperative bullet points (what MUST appear in the mockup).
"""
PLANNER_USER_TMPL = """Requirements:
Produce the JSON as specified. No prose, only JSON.
"""

IMAGE_PROMPT_TMPL = """Design a {platform} UI mockup for "{screen_name}".

GOAL:
{goal}

MUST INCLUDE (no exceptions):
- {must_lines}

LAYOUT SKETCH (textual blueprint, respect hierarchy and spacing):
{layout}

COMPONENT VOCABULARY:
{components}

STYLE (locked):
- Tone: {tone}
- Color: {color}
- Density: {density}
- Typography: {typography}
- Real, readable labels (no lorem)
- Accessible contrast ≥ 4.5:1
- Tap/click targets ≥ 44×44

DO NOT:
- Do not hallucinate extra tabs/sections not listed
- Do not add placeholder lorem
- Do not mirror platform UI conventions incorrectly

Output: one clean final composition centered on this single screen.
"""

def build_planner_prompt(requirements_text: str) -> Dict[str, str]:
    return {
        "system": PLANNER_SYSTEM,
        "user": PLANNER_USER_TMPL.format(req=requirements_text[:12000])
    }

def build_image_prompt(screen: Dict, global_style: Dict, platform: str="Web") -> str:
    must_lines = "\n- ".join(screen.get("must", []) or ["Key labels present", "Visible primary CTA"])
    return IMAGE_PROMPT_TMPL.format(
        platform=platform,
        screen_name=screen.get("name","Screen"),
        goal=screen.get("goal","Show the primary task clearly"),
        must_lines=must_lines,
        layout=screen.get("layout","Header > Filters > Content list/table > Footer"),
        components=", ".join(screen.get("components", []) or ["Search", "Filter chips", "Cards", "CTA", "Tabs"]),
        tone=screen.get("tone") or global_style.get("tone","clean, institutional"),
        color=screen.get("color") or global_style.get("color","light with brand accent"),
        density=screen.get("density") or global_style.get("density","medium"),
        typography=(global_style.get("typography") or "Inter / Roboto")
    )

# ============================================================================================
# OpenAI helpers
# ============================================================================================
def plan_screens_from_requirements(req_text: str) -> Dict[str, Any]:
    """Use a text model to turn the doc into a structured UI plan."""
    prompts = build_planner_prompt(req_text)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",              # inexpensive + good for planning
        messages=[
            {"role":"system","content":prompts["system"]},
            {"role":"user","content":prompts["user"]}
        ],
        temperature=0.2
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except Exception:
        # salvage JSON if wrapped in code fences
        start = raw.find("{"); end = raw.rfind("}")
        return json.loads(raw[start:end+1])

def generate_images_from_plan(plan: Dict[str,Any], platform="Web", n_per_screen=1, size="1024x1024") -> List[Dict[str,Any]]:
    """
    Generates images per screen in the plan. Returns list of dicts:
    {screen, index, prompt, b64}
    """
    out = []
    screens = plan.get("screens", [])
    global_style = plan.get("global_style", {})

    # Optional mock mode (set MOCK_MODE=true in .env to test without image model access)
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"

    for s in screens:
        prompt = build_image_prompt(s, global_style, platform=platform)
        if mock_mode:
            # Use placeholder images to let the pipeline run offline
            import requests
            sample = "https://placehold.co/1024x1024?text=Mockup+Preview"
            img_bytes = requests.get(sample, timeout=30).content
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            out.append({"screen": s.get("name","Screen"), "index": 1, "prompt": prompt, "b64": b64})
            continue

        # Real image generation
        resp = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            n=n_per_screen,
            size=size
        )
        for i, item in enumerate(resp.data, start=1):
            out.append({
                "screen": s.get("name","Screen"),
                "index": i,
                "prompt": prompt,
                "b64": item.b64_json
            })
    return out

def vision_check_adherence(image_b64: str, screen_spec: Dict[str,Any]) -> str:
    """
    Optional: have a vision-capable model check if the image matches the MUST list.
    Returns a short bullet report. Safe to skip if you don't want this step.
    """
    must = screen_spec.get("must", []) or []
    if not must: 
        return "No MUST items provided."

    content = [
        {"type":"text","text":"Check if this UI mockup includes ALL of the following items:\n- "+"\n- ".join(must)},
        {"type":"input_image","image_data":image_b64}
    ]
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":content}],
            temperature=0.2
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(Adherence check skipped: {e})"

def to_data_url(png_b64: str) -> str:
    return "data:image/png;base64," + png_b64

# ============================================================================================
# Streamlit App
# ============================================================================================
uploaded = st.file_uploader("Upload your requirement doc (txt, md, docx, pdf)", type=["txt","md","docx","pdf"])
gen_col, figma_col = st.columns([3,2])

# -------------------------------- PLAN STEP --------------------------------
with gen_col:
    if uploaded:
        raw_text = read_file_text(uploaded)
        st.subheader("Extracted requirements")
        st.text_area("Preview", raw_text[:5000], height=200)

        if not OPENAI_API_KEY:
            st.error("OPENAI_API_KEY is missing. Add it to your .env file at repo root.")
        else:
            if st.button("🧠 Plan Screens from Requirements"):
                with st.spinner("Planning screens..."):
                    try:
                        plan = plan_screens_from_requirements(raw_text)
                        st.session_state["plan"] = plan
                        st.success("Planned successfully. Review below.")
                    except Exception as e:
                        st.error(f"Planner error: {e}")

# Show / allow editing the plan
if "plan" in st.session_state:
    st.subheader("Planned UI (editable)")
    plan_str = st.text_area("Plan JSON", json.dumps(st.session_state["plan"], indent=2), height=280)
    try:
        edited_plan = json.loads(plan_str)
    except Exception:
        edited_plan = st.session_state["plan"]

    platform = st.selectbox("Platform", ["Web","Mobile"], index=0)
    n_per_screen = st.number_input("Images per screen", 1, 3, 1)
    size = st.selectbox("Image size", ["1024x1024","1024x1536","1365x768"], index=0)

    if st.button("🎨 Generate Mockups from Plan"):
        with st.spinner("Generating mockups…"):
            try:
                results = generate_images_from_plan(edited_plan, platform=platform, n_per_screen=n_per_screen, size=size)
                st.session_state["mockups"] = []
                for r in results:
                    name = f"{r['screen']}_{r['index']}.png"
                    st.session_state["mockups"].append({
                        "name": name,
                        "data": to_data_url(r["b64"]),
                        "prompt": r["prompt"],
                        "spec": r,
                        "screen_spec": next((s for s in edited_plan.get("screens", []) if s.get("name")==r["screen"]), {})
                    })
                st.success(f"Generated {len(st.session_state['mockups'])} mockups.")
            except Exception as e:
                st.error(f"OpenAI error: {e}")

# -------------------------------- RENDER IMAGES + OPTIONAL VERIFY --------------------------------
if "mockups" in st.session_state and st.session_state["mockups"]:
    st.subheader("Generated Mockups")
    for item in st.session_state["mockups"]:
        st.image(item["data"], caption=item["name"])
        with st.expander("Prompt used"):
            st.code(item["prompt"])
        # Optional adherence check (can be slow; enable per-image)
        if st.checkbox(f"Check adherence for {item['name']}", value=False):
            with st.spinner("Reviewing image…"):
                # pass pure b64 (strip 'data:image/png;base64,')
                pure_b64 = item["data"].split(",",1)[1]
                report = vision_check_adherence(pure_b64, item.get("screen_spec", {}))
                st.markdown(report)

# -------------------------------- SEND TO FIGMA BUNDLE --------------------------------
with figma_col:
    st.subheader("Send to Figma")
    st.markdown("Paste this bundle into the **Figma plugin** to import frames:")
    bundle = {"images": []}
    if "mockups" in st.session_state:
        for item in st.session_state["mockups"]:
            bundle["images"].append({
                "name": item["name"],
                "data": item["data"],   # base64 data URL (no hosting needed)
                # For production, prefer: "url": "https://.../mockup.png"
            })
    st.code(json.dumps(bundle, indent=2))
    st.info("The Figma plugin supports `data` (base64) and `url` (https). For production, host images and provide URLs.")

st.divider()
st.subheader("Notes")
st.markdown("""
- **Planner** uses `gpt-4o-mini` to convert your doc into structured screens with MUST-have items.
- **Image generation** uses `gpt-image-1`. If your org isn’t verified for images yet,
  set `MOCK_MODE=true` in `.env` to test the entire flow with placeholders.
- **Adherence check** is optional and uses a vision-capable chat model to verify MUST items.
""")
