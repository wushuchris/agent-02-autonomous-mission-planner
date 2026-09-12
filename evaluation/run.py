"""Run with python -m evaluation.run; nonzero exit means an expectation failed."""
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from evaluation.cases import cases
from models import MissionPlan, MissionRequest
from validator import validate_plan


def evaluate():
    rows = []
    for case in cases():
        request = MissionRequest.model_validate(case['request'])
        schema = True
        result = None
        try:
            plan = MissionPlan.model_validate(case['plan'])
        except ValidationError:
            schema = False
        else:
            result = validate_plan(request, plan)
        valid = result.valid if result else False
        checks = [schema == case['expected_schema'], valid == case['expected_valid']]
        if case['issue']:
            checks.append(bool(result and getattr(result, case['issue'])))
        if case['warning']:
            checks.append(bool(result and any(case['warning'] in w for w in result.warnings)))
        rows.append(dict(name=case['name'], group=case['group'], passed=all(checks),
                         expected_schema=case['expected_schema'], actual_schema=schema,
                         expected_valid=case['expected_valid'], actual_valid=valid,
                         errors=result.errors if result else ['Schema rejected'],
                         warnings=result.warnings if result else []))
    groups = {group: {'passed': sum(r['passed'] for r in rows if r['group'] == group),
                      'total': sum(r['group'] == group for r in rows)}
              for group in ('success', 'edge', 'failure', 'adversarial')}
    return dict(scope='Synthetic deterministic proposal evaluation; no live model calls',
                passed=sum(r['passed'] for r in rows), total=len(rows), groups=groups,
                limitations=['No live-model quality or prompt-injection resistance measurement',
                             'Constraint representation is not semantic adherence',
                             'Milestone presence is not verified milestone coverage',
                             'Resource scheduling/capacity and missing factual information require human review'],
                cases=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Save a JSON scorecard')
    args = parser.parse_args()
    report = evaluate()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"Expected outcomes: {report['passed']}/{report['total']}")
    for name, counts in report['groups'].items():
        print(f"{name}: {counts['passed']}/{counts['total']}")
    for row in report['cases']:
        if not row['passed']:
            print(f"FAIL: {row['name']}")
    raise SystemExit(0 if report['passed'] == report['total'] else 1)


if __name__ == '__main__':
    main()
