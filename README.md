# Search and Rescue Mission Planning Agent

Agent 2 in my **30 Agents for AI Engineers** portfolio.

This project is a human-in-the-loop mission planning assistant for search and rescue scenarios. It converts high-level rescue intent into structured mission plans with search phases, asset allocation, risks, communication checkpoints, safety considerations, and next best actions.

## Important Disclaimer

This project is an educational portfolio prototype for search and rescue planning. It is not a production emergency response system, does not replace trained responders or incident commanders, and should not be used for real-world mission execution without proper validation, safety controls, legal review, and human supervision.

## Project Purpose

Search and rescue operations often require teams to make decisions under uncertainty, limited visibility, changing weather, terrain constraints, and incomplete information.

This agent demonstrates how an AI planning system can help organize a safe and structured response plan for humanitarian and emergency scenarios. It is designed to support planning, not replace trained responders or incident commanders.

## What the Agent Does

The agent takes mission inputs such as:

- Rescue objective
- Search environment
- Search area
- Available assets
- Sensor payloads
- Operational constraints
- Human approval rules
- Success criteria
- Planning depth

It returns a structured mission plan with:

- Mission summary
- Mission assumptions
- Search phases
- Asset allocation
- Dependencies
- Risk assessment
- Human-in-the-loop checkpoints
- Safe response recommendations
- Success criteria review
- Next best action

## Safety Boundary

This project is designed for humanitarian, emergency response, and public safety planning. It does not provide support for weaponization, targeting, attack planning, evasion, or harmful engagement logic.

The agent focuses on:

- Search and rescue
- Missing person response
- Disaster response
- Infrastructure inspection after emergencies
- Wilderness search planning
- Flood, wildfire, or earthquake response
- Operator alerts
- Human approval workflows

## Example Use Case

An incident coordinator provides the following intent:

> Search a 30-meter area around the last known location of a missing hiker, complete one full sweep, report findings, identify possible hazards, and recommend the next safest search action.

The agent converts that intent into a structured plan with search phases, asset tasking, risks, checkpoints, and next actions.

## Tech Stack

- Python
- Streamlit
- Hugging Face Inference API
- Mistral-7B-Instruct
- python-dotenv

## Portfolio Context

This is part of my broader **30 Agents for AI Engineers** learning portfolio.

Agent 1 focused on autonomous decision-making.

Agent 2 focuses on planning: decomposing a complex objective into structured, executable steps with dependencies, risks, and human oversight.

## Disclaimer

This project is for educational and portfolio purposes. It is not a production emergency response system and should not be used for real-world mission execution without trained responders, appropriate engineering validation, safety controls, legal review, and human supervision.