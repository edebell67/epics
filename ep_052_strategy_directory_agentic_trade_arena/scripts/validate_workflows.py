# scripts/validate_workflows.py — Validate workflow contracts, links and plan-only status.
# VERSION HISTORY
# v1.1.0 · 2026-09-02 · Require completed nodes to carry evidence and testable deliverable.
# v1.0.0 · 2026-09-02 · Checks the lean maps without claiming application execution.
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src'):
                self.links.append(value)


def validate(phase='master'):
    raw = (ROOT / 'workflows/workflow-data.js').read_text(encoding='utf-8')
    data = json.loads(raw.split('window.EP052_WORKFLOW=', 1)[1].rstrip().removesuffix(';'))
    nodes = data['nodes'] if phase == 'master' else [n for n in data['nodes'] if n['lane'].lower() == phase]
    assert nodes, 'Unknown or empty phase'
    assert len({n['id'] for n in data['nodes']}) == 24
    assert len(data['phases']) == 6
    for node in nodes:
        for field in ('id', 'title', 'inputs', 'steps', 'test', 'evidence', 'dependencies', 'executor', 'outputs'):
            assert node[field], (node['id'], field)
        assert 0 <= node['pct'] <= 100
        if node['pct'] == 100:
            assert node['status'] == 'Complete' and node.get('deliverable')
            assert not node['evidence'].startswith('Planned:')
        else:
            assert node['status'] != 'Complete'
    pages = [ROOT / 'EP052_lean_implementation_workflow.html',
             ROOT / 'EP052_lean_implementation_checklist.html',
             *sorted((ROOT / 'workflows').glob('EP052_l*_workflow.html'))]
    assert len(pages) == 8
    for page in pages:
        parser = Links()
        parser.feed(page.read_text(encoding='utf-8'))
        for href in parser.links:
            target = (page.parent / href.split('#', 1)[0]).resolve()
            assert target.is_relative_to(ROOT), (page.name, 'escaped root', href)
            assert target.exists(), (page.name, 'missing link', href)
    for item in ['master', *[p['id'].lower() for p in data['phases']]]:
        assert (ROOT / f'skills/ep052-{item}/SKILL.md').is_file()
    print(f'PASS: {len(nodes)} selected leaf contracts; 8 HTML files; 7 map guides; all local links resolve.')
    print('Completed gates:', sum(n['pct'] == 100 for n in data['nodes']), '/ 24; validator does not replace runtime acceptance.')


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--phase', default='master', choices=['master', 'l1', 'l2', 'l3', 'l4', 'l5', 'l6'])
    validate(args.parse_args().phase)
