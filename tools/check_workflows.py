"""Cheap Actions-only syntax check; catches broken inline Python before builds."""
import ast
from pathlib import Path
import re
import yaml

for file in Path('.github/workflows').glob('*.yml'):
    workflow = yaml.load(file.read_text(), Loader=yaml.BaseLoader)
    assert 'on' in workflow and 'jobs' in workflow, file
    for job in workflow['jobs'].values():
        for step in job.get('steps', []):
            script = step.get('run', '')
            for match in re.finditer(r"python3? - <<'PY'\n(.*?)\nPY(?:\n|$)", script, re.S):
                ast.parse(match.group(1), filename=str(file))
for file in [*Path('tools').glob('*.py'), *Path('tests').glob('*.py')]:
    ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
print('Workflow YAML and Python syntax PASS (not product qualification)')
