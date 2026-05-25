import os
import streamlit as st
from dotenv import load_dotenv
from huggingface_hub import InferenceClient


load_dotenv()


st.set_page_config(
    page_title="Search and Rescue Mission Planning Agent",
    page_icon="🚁",
    layout="wide"
)


def get_hf_token():
    """Load Hugging Face token from Streamlit secrets or environment variables."""
    try:
        return st.secrets["HF_TOKEN"]
    except Exception:
        return os.getenv("HF_TOKEN")


def build_prompt(
    rescue_objective,
    search_environment,
    search_area,
    available_assets,
    sensors,
    constraints,
    human_approval_rules,
    success_criteria,
    planning_depth
):
    """Create the search and rescue planning prompt for the model."""

    return f"""
You are a Search and Rescue Mission Planning Agent.

Your job is to convert high-level rescue intent into a structured, human-in-the-loop search and rescue mission plan.

Important safety rules:
- Focus only on humanitarian, emergency response, missing person, disaster response, inspection, and public safety scenarios.
- Do not provide weaponization, targeting, attack, evasion, or harmful engagement instructions.
- Do not replace trained responders, incident commanders, emergency services, or legal authority.
- Emphasize human oversight, responder safety, communication, risk awareness, and responsible use of autonomous systems.
- Keep recommendations practical, non-violent, and operator-approved.

Mission Inputs:
Rescue Objective: {rescue_objective}
Search Environment: {search_environment}
Search Area: {search_area}
Available Assets: {available_assets}
Sensors: {sensors}
Operational Constraints: {constraints}
Human Approval Rules: {human_approval_rules}
Success Criteria: {success_criteria}
Planning Depth: {planning_depth}

Return the mission plan in clear Markdown using this structure:

# Search and Rescue Mission Plan

## 1. Mission Summary
Summarize the rescue mission in plain English.

## 2. Mission Assumptions
List key assumptions and uncertainties.

## 3. Search Phases
Create phased steps from initial setup through search completion.

## 4. Asset Allocation
Explain how each drone, responder, sensor, or support asset should be used.

## 5. Dependencies
List what must be true before or during the mission.

## 6. Risk Assessment
Identify operational, environmental, technical, and human safety risks.

## 7. Human-in-the-Loop Checkpoints
List points where a human operator, responder, or incident lead must review, confirm, or approve.

## 8. Safe Response Recommendations
Suggest safe options such as continue search, widen search area, mark point of interest, request responder review, return to base, preserve battery, or escalate to trained personnel.

## 9. Success Criteria Review
Explain how to evaluate whether the search mission succeeded.

## 10. Next Best Action
Give the immediate next action for the operator or incident coordinator.

Keep the plan practical, concise, safety-focused, and appropriate for educational portfolio use.
"""


def generate_plan(prompt):
    """Generate a search and rescue mission plan using Hugging Face InferenceClient."""

    hf_token = get_hf_token()

    if not hf_token:
        return """
⚠️ Hugging Face token not found.

To run the live model, add your token as `HF_TOKEN` in Streamlit secrets or your local `.env` file.
"""

    client = InferenceClient(
        model="mistralai/Mistral-7B-Instruct-v0.3",
        token=hf_token
    )

    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful, safety-focused search and rescue planning assistant. "
                    "You support humanitarian planning only and do not provide harmful, weaponized, "
                    "or tactical engagement guidance."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=1400,
        temperature=0.4
    )

    return response.choices[0].message.content


st.title("Search and Rescue Mission Planning Agent")
st.caption(
    "A human-in-the-loop planning assistant for drone-supported search and rescue missions."
)

st.warning(
    "Educational prototype only. This app does not replace trained responders, emergency services, "
    "incident commanders, legal authority, or real-world safety procedures."
)

with st.sidebar:
    st.header("About This Agent")
    st.write(
        "This app demonstrates a planning agent for humanitarian search and rescue scenarios. "
        "It helps organize rescue objectives into structured search phases, asset allocation, "
        "risk assessment, human checkpoints, and next actions."
    )

    st.header("Safety Boundary")
    st.write(
        "The agent is designed for missing person response, disaster response, infrastructure inspection, "
        "wilderness search planning, and emergency coordination. It does not support weaponization, "
        "targeting, attack planning, evasion, or harmful engagement logic."
    )


col1, col2 = st.columns(2)

with col1:
    rescue_objective = st.text_area(
        "Rescue Objective",
        value=(
            "Search a 30-meter area around the last known location of a missing hiker, "
            "complete one full sweep, report findings, identify possible hazards, and recommend "
            "the next safest search action."
        ),
        height=140
    )

    search_environment = st.text_area(
        "Search Environment",
        value=(
            "Wilderness trail area, late afternoon, moderate tree cover, uneven terrain, "
            "limited visibility in some sections."
        ),
        height=100
    )

    search_area = st.text_input(
        "Search Area",
        value="30-meter radius around the missing person's last known location"
    )

    available_assets = st.text_area(
        "Available Assets",
        value=(
            "2 small drones with cameras, 1 ground search team, 1 incident coordinator, "
            "basic first aid supplies, and radio communication."
        ),
        height=100
    )

with col2:
    sensors = st.text_area(
        "Sensors",
        value="RGB cameras, GPS positioning, telemetry feed, basic object detection.",
        height=100
    )

    constraints = st.text_area(
        "Operational Constraints",
        value=(
            "Preserve battery life, avoid flying beyond visual line of sight, maintain communication "
            "with the ground team, avoid hazardous terrain, and do not move into unsafe areas without responder review."
        ),
        height=120
    )

    human_approval_rules = st.text_area(
        "Human Approval Rules",
        value=(
            "The incident coordinator must confirm the search area, review the initial sweep report, "
            "approve any search area expansion, and coordinate any physical response with trained personnel."
        ),
        height=100
    )

    success_criteria = st.text_area(
        "Success Criteria",
        value=(
            "The team completes one structured sweep, identifies hazards and points of interest, "
            "documents findings, preserves responder safety, and recommends the next search action."
        ),
        height=100
    )

planning_depth = st.selectbox(
    "Planning Depth",
    options=["Quick", "Standard", "Detailed"],
    index=1
)

generate_button = st.button("Generate Search and Rescue Plan", type="primary")

if generate_button:
    with st.spinner("Generating search and rescue plan..."):
        prompt = build_prompt(
            rescue_objective,
            search_environment,
            search_area,
            available_assets,
            sensors,
            constraints,
            human_approval_rules,
            success_criteria,
            planning_depth
        )

        plan = generate_plan(prompt)

    st.subheader("Generated Search and Rescue Mission Plan")
    st.markdown(plan)

    st.download_button(
        label="Download Search and Rescue Plan",
        data=plan,
        file_name="search_and_rescue_mission_plan.md",
        mime="text/markdown"
    )