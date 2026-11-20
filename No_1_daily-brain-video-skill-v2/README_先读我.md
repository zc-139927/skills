# 每日脑力挑战视频 Skill v2.0（分类增强版）

## 本版新增

- 经过网页查阅、整理为 **16个内容类别、98个具体玩法**。见 `references/完整题型分类与玩法.md`；另有可程序读取的 `完整题型库.json`。
- 新增 **30天轮换选题工具**，不再只围绕3种视频反复旋转。
- 附生活习惯科普选题和研究来源、内容合规提醒。
- 完整保留旧版3种已验证的MP4制作程序。

## 特别注意

**功能不能混淆：** `scripts/plan_series.py` 能为16类、98玩法生成排期；`scripts/generate.py` 当前只会自动渲染3种（圆盘、小球、物品记忆）。其他题型尚需扩展动画模板。只有实际渲染得到MP4时才声称成片。

## 一键排期

```bash
python scripts/plan_series.py --start-day 4 --days 30 --output-dir output/plan30
```

## 已实现题型制作视频

```bash
python -m pip install -r requirements.txt
python scripts/generate.py --day 4 --preview
python scripts/generate.py --day 4 --output-dir output/day04
```

渲染需要系统安装FFmpeg及中文字体；可先参考 `references/使用与自定义.md`。

解压后将**整个文件夹**导入支持 `SKILL.md` 的智能体/Agent运行环境。ZIP 不会自行安装到ChatGPT。
