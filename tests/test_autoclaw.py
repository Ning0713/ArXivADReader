import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ops.qq_command import parse_command


@pytest.mark.parametrize(('message', 'project', 'command', 'day'), [
    ('情感计算 补跑 2026-09-16', 'ac', 'retry', '2026-09-16'),
    ('自动驾驶 预览 today', 'ad', 'preview', 'today'),
    ('全部 更新论文', 'all', 'update', 'today'),
    ('全部 状态', 'all', 'status', ''),
    ('更新论文', 'ad', 'update', 'today'),
])
def test_qq_routes(message, project, command, day):
    assert parse_command(message) == {'project': project, 'command': command, 'date': day}


def test_default_is_explicit_and_legacy_compatible():
    assert parse_command('更新论文', 'ac')['project'] == 'ac'
    assert parse_command('更新论文', 'ad')['project'] == 'ad'


@pytest.mark.parametrize('message', [
    '情感计算 补跑 2026-02-30',
    '全部 补跑',
    '情感计算 状态 2026-09-16',
    '自动驾驶 更新; whoami',
    'ac 更新 $(whoami)',
    '新领域 更新',
    '全部 更新 2026-09-16\nwhoami',
    '情感计算 预览 "2026-09-16"',
])
def test_invalid_command_is_rejected(message):
    with pytest.raises(ValueError):
        parse_command(message)


@pytest.mark.skipif(not shutil.which('powershell.exe'), reason='Windows entry point')
@pytest.mark.parametrize(('command', 'force', 'dry'), [
    ('update', 'false', 'false'),
    ('retry', 'true', 'false'),
    ('preview', 'true', 'true'),
])
def test_powershell_routes_both_repositories_without_dispatch(command, force, dry):
    script = Path(__file__).resolve().parents[1] / 'ops' / 'autoclaw.ps1'
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script),
         command, '2026-09-16', '-Project', 'all', '-PlanOnly'],
        capture_output=True,
        text=True,
        check=True,
    )
    plans = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert [p['repository'] for p in plans] == [
        'Ning0713/ArXivADReader', 'Ning0713/ArXivACReader'
    ]
    for plan in plans:
        assert f'force={force}' in plan['arguments']
        assert f'dry_run={dry}' in plan['arguments']
        assert 'date=2026-09-16' in plan['arguments']
