"""Publish only the application files; preserve Space metadata and secrets."""
import os
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd

SPACE = 'FlyingNunchucks/search-and-rescue-mission-planner'
ROOT = Path(__file__).resolve().parents[1]
FILES = {'app.py': 'src/streamlit_app.py', 'requirements.txt': 'requirements.txt'}
for name in ('models', 'planner', 'plan_graph', 'validator', 'planning_engine', 'approval', 'audit'):
    FILES[f'{name}.py'] = f'src/{name}.py'


def main():
    token = os.environ.get('HF_TOKEN')
    if not token:
        raise SystemExit('Missing repository Actions secret HF_TOKEN.')
    api = HfApi(token=token)
    info = api.space_info(SPACE)
    result = api.create_commit(
        repo_id=SPACE, repo_type='space', parent_commit=info.sha,
        operations=[CommitOperationAdd(path_in_repo=target, path_or_fileobj=ROOT / source)
                    for source, target in FILES.items()],
        commit_message=f"Deploy GitHub revision {os.environ.get('GITHUB_SHA', 'manual')}",
    )
    print(f'Deployed {len(FILES)} files to {SPACE}; Space commit: {result.oid}')


if __name__ == '__main__':
    main()
