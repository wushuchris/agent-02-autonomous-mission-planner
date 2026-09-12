"""Dependency graph inspection without LLM calls or third-party graph packages."""
from collections import Counter
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter

from models import MissionPlan


@dataclass
class PlanGraph:
    dependencies: dict[str, list[str]]
    topological_order: list[str]
    errors: list[str]


def build_plan_graph(plan: MissionPlan) -> PlanGraph:
    counts = Counter(task.task_id for task in plan.tasks)
    errors = [f"Duplicate task ID: {task_id}" for task_id, count in counts.items() if count > 1]
    # Do not silently overwrite duplicate nodes or invent missing dependency nodes.
    dependencies = {}
    for task in plan.tasks:
        for dependency in task.dependencies:
            if dependency not in counts:
                errors.append(f"Task {task.task_id} references nonexistent dependency: {dependency}")
        if counts[task.task_id] == 1:
            dependencies[task.task_id] = list(task.dependencies)
    order = []
    if not errors:
        try:
            order = list(TopologicalSorter(dependencies).static_order())
        except CycleError as exc:
            errors.append("Circular dependencies: " + " -> ".join(exc.args[1]))
    return PlanGraph(dependencies, order, errors)
