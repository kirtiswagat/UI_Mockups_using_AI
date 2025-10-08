# UI_PROMPT_TEMPLATE = """You are a senior product designer.
# Generate a clean, modern UI mockup for: {title}

# Constraints:
# - Platform: {platform}
# - Overall vibe: {vibe}
# - Color direction: {color_direction}
# - Density: {density}
# - Primary screen(s): {screens}
# - Use real, readable labels (no lorem ipsum)
# - Include clear visual hierarchy, spacing, and accessible contrast
# - Show common components if relevant: search, filter chips, tabs, cards, CTAs
# - Include one hero section where appropriate
# - Keep style consistent and production-friendly

# Output format: a single detailed prompt describing the UI scene(s) to visualize.
# """


# def build_prompt(requirements_text: str) -> str:
#     title = "UI Mockups — Generated Screen"
#     platform = "Mobile" if "mobile" in requirements_text.lower() else "Web"
#     vibe = "friendly and premium"
#     color_direction = "light with brand accent"
#     density = "airy"
#     screens = "Home and a list of items with filters"

#     prompt = UI_PROMPT_TEMPLATE.format(
#         title=title,
#         platform=platform,
#         vibe=vibe,
#         color_direction=color_direction,
#         density=density,
#         screens=screens,
#     )
#     prompt += "\n\nSpecific Requirements (verbatim from user doc, truncated):\n"
#     prompt += requirements_text[:4000]
#     return prompt

from typing import List, Dict

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

Output: one clean final composition centered on this single screen."""

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

