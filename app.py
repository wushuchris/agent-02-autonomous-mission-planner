import os
import re
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from models import MissionRequest, PlanningDepth
from planner import PlannerOutputError, generate_structured_plan, plan_to_markdown
from plan_graph import build_plan_graph
from validator import apply_validation_status, validate_plan


load_dotenv()


st.set_page_config(
    page_title="Search and Rescue Mission Planning Agent",
    page_icon="🚁",
    layout="wide",
)


def get_hf_token():
    """Load Hugging Face token from Streamlit secrets or environment variables."""
    try:
        return st.secrets["HF_TOKEN"]
    except Exception:
        return os.getenv("HF_TOKEN")


def parse_list_input(value: str) -> list[str]:
    """Convert comma- or newline-separated UI text into clean structured entries."""
    entries = re.split(r",|\n", value)
    cleaned: list[str] = []

    for entry in entries:
        item = entry.strip().strip(".")
        if item.lower().startswith("and "):
            item = item[4:].strip()
        if item:
            cleaned.append(item)

    return cleaned


def build_mission_request(
    rescue_objective: str,
    search_environment: str,
    search_area: str,
    available_assets: str,
    sensors: str,
    constraints: str,
    human_approval_rules: str,
    success_criteria: str,
    planning_depth: str,
) -> MissionRequest:
    """Translate Streamlit form values into the reusable planning contract."""
    return MissionRequest(
        mission_id=f"sar-{uuid4().hex[:12]}",
        objective=rescue_objective,
        environment=search_environment,
        search_area=search_area,
        available_resources=parse_list_input(available_assets),
        sensors=parse_list_input(sensors),
        constraints=parse_list_input(constraints),
        approval_rules=parse_list_input(human_approval_rules),
        success_criteria=parse_list_input(success_criteria),
        planning_depth=PlanningDepth(planning_depth),
    )


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
        "This app demonstrates a reusable planning-agent pattern through a humanitarian search and rescue scenario. "
        "It converts mission intent into a typed, machine-readable plan before presenting a human-readable version."
    )

    st.header("Engineering Pattern")
    st.write("**The LLM proposes. Rules validate. The agent replans. Humans approve.**")
    st.caption(
        "Current upgrade stage: structured planning, schema validation and deterministic graph checks. "
        "Bounded replanning and human decision capture remain future phases."
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
        height=140,
    )

    search_environment = st.text_area(
        "Search Environment",
        value=(
            "Wilderness trail area, late afternoon, moderate tree cover, uneven terrain, "
            "limited visibility in some sections."
        ),
        height=100,
    )

    search_area = st.text_input(
        "Search Area",
        value="30-meter radius around the missing person's last known location",
    )

    available_assets = st.text_area(
        "Available Assets",
        value=(
            "2 small drones with cameras, 1 ground search team, 1 incident coordinator, "
            "basic first aid supplies, and radio communication."
        ),
        height=100,
        help="Separate resources with commas or new lines.",
    )

with col2:
    sensors = st.text_area(
        "Sensors",
        value="RGB cameras, GPS positioning, telemetry feed, basic object detection.",
        height=100,
        help="Separate sensors with commas or new lines.",
    )

    constraints = st.text_area(
        "Operational Constraints",
        value=(
            "Preserve battery life, avoid flying beyond visual line of sight, maintain communication "
            "with the ground team, avoid hazardous terrain, and do not move into unsafe areas without responder review."
        ),
        height=120,
        help="Separate constraints with commas or new lines.",
    )

    human_approval_rules = st.text_area(
        "Human Approval Rules",
        value=(
            "The incident coordinator must confirm the search area, review the initial sweep report, "
            "approve any search area expansion, and coordinate any physical response with trained personnel."
        ),
        height=100,
        help="Separate approval rules with commas or new lines.",
    )

    success_criteria = st.text_area(
        "Success Criteria",
        value=(
            "The team completes one structured sweep, identifies hazards and points of interest, "
            "documents findings, preserves responder safety, and recommends the next search action."
        ),
        height=100,
        help="Separate success criteria with commas or new lines.",
    )

planning_depth = st.selectbox(
    "Planning Depth",
    options=[depth.value for depth in PlanningDepth],
    index=1,
)

generate_button = st.button("Generate Structured Search and Rescue Plan", type="primary")

if generate_button:
    for key in ("mission_plan", "mission_request", "validation_result"):
        st.session_state.pop(key, None)
    try:
        mission_request = build_mission_request(
            rescue_objective=rescue_objective,
            search_environment=search_environment,
            search_area=search_area,
            available_assets=available_assets,
            sensors=sensors,
            constraints=constraints,
            human_approval_rules=human_approval_rules,
            success_criteria=success_criteria,
            planning_depth=planning_depth,
        )

        with st.spinner("Generating structured search and rescue plan..."):
            plan = generate_structured_plan(
                mission_request=mission_request,
                hf_token=get_hf_token(),
            )

        validation = validate_plan(mission_request, plan)
        plan = apply_validation_status(plan, validation)
        st.session_state["validation_result"] = validation
        st.session_state["mission_request"] = mission_request
        st.session_state["mission_plan"] = plan

    except ValidationError as exc:
        st.error("The mission request did not satisfy the planning input schema.")
        st.code(str(exc))
    except PlannerOutputError as exc:
        st.error(str(exc))
        st.info(
            "The planner failed closed rather than accepting malformed model output. "
            "Try generating the plan again or revise the mission inputs."
        )
    except Exception:
        st.error(
            "The planning service encountered an unexpected error. "
            "No plan was accepted. Please try again."
        )


if "mission_plan" in st.session_state:
    plan = st.session_state["mission_plan"]
    mission_request = st.session_state["mission_request"]
    validation = st.session_state["validation_result"]
    plan_markdown = plan_to_markdown(plan)
    plan_markdown += "\n\n## Deterministic Validation\n"
    plan_markdown += "PASS" if validation.valid else "FAIL — proposal requires correction"
    plan_markdown += "\n" + "\n".join(f"- {item}" for item in validation.errors + validation.warnings)
    plan_json = plan.model_dump_json(indent=2)

    st.divider()
    st.subheader("Generated Search and Rescue Mission Plan")

    status_col, validation_col, mission_col = st.columns(3)
    status_col.metric("Schema Status", "VALID")
    validation_col.metric("Deterministic Checks", "PASS" if validation.valid else "FAIL")
    mission_col.metric("Plan Status", plan.plan_status.value)

    st.success(
        "The model output was successfully parsed into the MissionPlan Pydantic schema. "
        "This confirms structure and types, not plan correctness."
    )

    if validation.valid:
        st.info("Deterministic checks passed. This is an advisory proposal awaiting human review, not authorization to execute.")
    else:
        st.error("Deterministic validation failed. This proposal must be corrected before use. Automatic replanning is not implemented.")
    for error in validation.errors:
        st.error(error)
    for warning in validation.warnings:
        st.warning(warning)
    with st.expander("View Dependency Graph"):
        graph = build_plan_graph(plan)
        st.json({"dependencies": graph.dependencies, "topological_order": graph.topological_order, "errors": graph.errors})
        st.caption("Dependencies list each task's prerequisites. The ordering is structural, not an execution schedule. Invalid graphs have no ordering.")
    with st.expander("View Deterministic Validation JSON"):
        st.json(validation.model_dump(mode="json"))
    st.download_button("Download Validation JSON", validation.model_dump_json(indent=2),
                       "plan_validation.json", "application/json")
    st.markdown(plan_markdown)

    with st.expander("View Structured Mission Request"):
        st.json(mission_request.model_dump(mode="json"))

    with st.expander("View Structured MissionPlan JSON"):
        st.json(plan.model_dump(mode="json"))

    download_col1, download_col2 = st.columns(2)

    with download_col1:
        st.download_button(
            label="Download Human-Readable Plan",
            data=plan_markdown,
            file_name="search_and_rescue_mission_plan.md",
            mime="text/markdown",
        )

    with download_col2:
        st.download_button(
            label="Download Structured Plan JSON",
            data=plan_json,
            file_name="search_and_rescue_mission_plan.json",
            mime="application/json",
        )
