#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""Create an across-family, non-video content plan from the verified JSON catalog."""
import json,csv,random,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def create_plan(start_day=4,days=30,seed=20261120):
    db=json.loads((ROOT/'references'/'完整题型库.json').read_text(encoding='utf-8'))
    families=db['families']
    rng=random.Random(seed)
    # First 16 videos start with audience-friendly, visually diverse concepts.
    curated=[0,5,10,8,2,4,1,7,6,3,9,13,11,12,14,15]
    preferred={
        '01':'不规则拼块舒尔特','06':'Stroop颜色文字冲突',
        '11':'图形旋转判断','09':'图形矩阵推理',
        '03':'多目标追踪','05':'数字倒背',
        '02':'找不同','08':'符号快速配对',
        '07':'形状颜色切换','04':'场景细节记忆',
        '10':'24点游戏','14':'声音序列位置',
        '12':'快速找错字','13':'最优路线规划',
        '15':'追踪小球同时计数','16':'表情线索辨别'
    }
    random_order=curated[:]
    # one pass through all families, then another shuffled pass.
    result=[]; last_family=None
    used={f['id']:set() for f in families}
    for i in range(days):
        if i%len(families)==0 and i>0:
            rng.shuffle(random_order)
            if last_family is not None and random_order[0]==last_family:
                random_order[0],random_order[1]=random_order[1],random_order[0]
        family=families[random_order[i%len(families)]]
        last_family=random_order[i%len(families)]
        available=[t for t in family['tasks'] if t['id'] not in used[family['id']] and t['video_fit']=='A']
        if not available: available=[t for t in family['tasks'] if t['id'] not in used[family['id']]]
        if not available:
            used[family['id']].clear(); available=list(family['tasks'])
        if i<len(families):
            task=next(t for t in family['tasks'] if t['name']==preferred[family['id']])
        else:
            task=rng.choice(available)
        used[family['id']].add(task['id'])
        n=i+start_day
        level=1+(i//len(families))%3
        rec={'期数':f'DAY {n:02d}','题型类别':family['name'],'挑战题目':task['name'],
             '玩法规则':task['rule'],'难度':('基础','进阶','高难')[level-1],
             '建议时长(秒)':task['suggested_seconds'],
             '自动生成MP4':('已支持' if task['auto_video_supported'] else '需要新增该题型模板'),
             '视频结构':'标题说明→互动倒计时→结束留言（不公开答案）'}
        result.append(rec)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--start-day',type=int,default=4)
    p.add_argument('--days',type=int,default=30)
    p.add_argument('--seed',type=int,default=20261120)
    p.add_argument('--output-dir',default='output/plan30')
    a=p.parse_args()
    assert 1 <= a.days <= 366
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    rows=create_plan(a.start_day,a.days,a.seed)
    with (out/'30天选题计划.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (out/'30天选题计划.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 跨题型每日脑力挑战排期','',f'从第{a.start_day}期开始，{a.days}天，每天一种玩法；同类型尽量避免相邻。','','| 期数 | 类别 | 题目 | 时长 | 当前渲染状态 |','|---|---|---|---:|---|']
    for x in rows: lines.append(f"| {x['期数']} | {x['题型类别']} | {x['挑战题目']} | {x['建议时长(秒)']}秒 | {x['自动生成MP4']} |")
    lines.append('\n注意：排期文件不是视频文件。此版本仅有3个视频自动渲染模板。')
    (out/'30天选题计划.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'Generated {len(rows)} planned episodes in {out.resolve()}')
