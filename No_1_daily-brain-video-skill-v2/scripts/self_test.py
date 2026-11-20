#!/usr/bin/env python3
"""Fast smoke test: creates all 3 types at preview size and verifies files/data."""
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='brain_skill_test_') as tmp:
    for day,kind in [(4,'disc'),(5,'balls'),(6,'memory')]:
        out=Path(tmp)/f'DAY{day:02d}'
        subprocess.run([sys.executable,str(ROOT/'scripts/generate.py'),'--day',str(day),
                        '--preview','--no-zip','--output-dir',str(out)],check=True)
        data=json.loads((out/'生成参数_质检.json').read_text(encoding='utf-8'))
        assert data['type']==kind and data['reveal_answers'] is False
        assert (out/f'DAY{day:02d}_{kind}_无答案版.mp4').stat().st_size>1000
        assert (out/'封面_题目.png').stat().st_size>1000
        if kind!='memory':
            assert sorted(data['numbers'])==list(range(1,50))
        else:
            assert len(data['items_in_row_major_order'])==12
            answers=json.loads((out/'创作者专用_答案.json').read_text(encoding='utf-8'))
            assert len(answers['questions'])==3
print('PASS: all 3 modes rendered, verified, and kept answer-free')
