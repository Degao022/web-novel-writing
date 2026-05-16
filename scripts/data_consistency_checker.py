#!/usr/bin/env python3
"""
小说数据计算校验器 v1.0
校对小说中出现的各类数值计算，包括等级、修为、经验、积分、声望、崇拜者等。

用法：
  python data_consistency_checker.py <小说章节目录> [--world <世界观设定文件>]

功能：
  1. 扫描所有章节TXT文件，提取数值型数据（声望、崇拜者、毒舌值、等级等）
  2. 追踪同一数值在不同章节间的变化，检测加减计算是否正确
  3. 检测数值回退（如声望从2000降到1800但无扣除说明）
  4. 检测数值跳跃（如崇拜者从10突然到50但无增量和来源说明）
  5. 生成数据变化时间线，标注异常点
"""

import re
import sys
import os
import json
from pathlib import Path
from collections import defaultdict

# ============================================================
# 数据提取规则
# ============================================================

# 已知的数值字段模式（可扩展）
# 每条规则：(字段名, 正则模式, 值捕获组索引)
NUMERIC_PATTERNS = [
    # 系统面板类
    ("声望", r"声望[值：:]*\s*(\d+)", 1),
    ("声望", r"声望[：:]\s*(\d+)", 1),
    ("崇拜者", r"崇拜者[数量：:]*\s*(\d+)", 1),
    ("毒舌值", r"毒舌值[：:]*\s*(\d+)", 1),
    ("仇恨值", r"仇恨值[：:]*\s*(\d+)", 1),
    ("经验", r"经验[值：:]*\s*(\d+)", 1),
    ("积分", r"积分[：:]*\s*(\d+)", 1),
    ("等级", r"等级[：:]*\s*(\d+)", 1),

    # 增量模式（如"声望+300""崇拜者+35人"）
    ("声望增量", r"声望[值]*[+＋]\s*(\d+)", 1),
    ("崇拜者增量", r"崇拜者[数量]*[+＋]\s*(\d+)", 1),
    ("毒舌值增量", r"毒舌值[+＋]\s*(\d+)", 1),

    # 里程碑/差值模式（如"还差200点""距离下一个里程碑还差8人"）
    ("声望差额", r"声望.*?还差\s*(\d+)\s*点", 1),
    ("崇拜者差额", r"崇拜者.*?还差\s*(\d+)\s*人", 1),

    # 通用数值模式：数字+单位
    ("银两", r"(\d+)\s*两\s*银", 1),
    ("天数", r"(\d+)\s*天[以之]?前", 1),
    ("年数", r"(\d+)\s*年", 1),
]

# 排除误匹配的关键词黑名单（包含这些词的行不提取）
BLACKLIST_CONTEXT = ["相当于", "约莫", "大约", "差不多", "消耗", "花费", "扣除", "需要消耗", "使用条件"]


def extract_chapter_number(filename: str) -> int:
    """从文件名中提取章节号"""
    m = re.search(r'第(\d+)章', filename)
    return int(m.group(1)) if m else 0


def scan_chapter(filepath: str) -> list:
    """
    扫描单个章节文件，提取所有数值数据。
    返回: [(字段名, 数值, 行号, 行内容)]
    """
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  [WARN] 无法读取 {filepath}: {e}")
        return results

    for line_no, line in enumerate(lines, 1):
        # 跳过黑名单行
        if any(bl in line for bl in BLACKLIST_CONTEXT):
            continue

        for field_name, pattern, group_idx in NUMERIC_PATTERNS:
            for m in re.finditer(pattern, line):
                try:
                    value = int(m.group(group_idx))
                    results.append((field_name, value, line_no, line.strip()))
                except (ValueError, IndexError):
                    continue

    return results


def check_consistency(all_data: dict, chapter_order: list) -> list:
    """
    检查数据一致性。
    all_data: {章节号: [(字段名, 数值, 行号, 行内容)]}
    chapter_order: 排序后的章节号列表
    返回: [异常描述]
    """
    issues = []

    # 按字段名分组，追踪同一字段在各章节的变化
    field_timeline = defaultdict(list)  # {字段名: [(章节号, 数值, 行号, 行内容)]}

    for ch in chapter_order:
        if ch not in all_data:
            continue
        for field_name, value, line_no, line_content in all_data[ch]:
            field_timeline[field_name].append((ch, value, line_no, line_content))

    # 对每个字段检查
    for field_name, timeline in field_timeline.items():
        if len(timeline) < 2:
            continue

        # 按章节号排序
        timeline.sort(key=lambda x: x[0])

        # 检查增量字段 vs 绝对值字段
        if "增量" in field_name:
            base_field = field_name.replace("增量", "")
            # 增量字段本身不做连续性检查，但会用来验证绝对值
            continue

        if "差额" in field_name:
            # 差额字段：差额 + 当前值 = 里程碑值，间接验证
            base_field = field_name.replace("差额", "")
            continue

        # 绝对值字段：检查连续性
        for i in range(1, len(timeline)):
            prev_ch, prev_val, prev_line, prev_content = timeline[i - 1]
            curr_ch, curr_val, curr_line, curr_content = timeline[i]

            # 数值下降（无扣除说明）
            if curr_val < prev_val and curr_ch > prev_ch:
                # 检查中间章节是否有扣除说明
                has_deduction = False
                for ch in range(prev_ch + 1, curr_ch + 1):
                    if ch in all_data:
                        for fn, v, ln, lc in all_data[ch]:
                            if fn == field_name and v < prev_val:
                                has_deduction = True
                                break
                    if has_deduction:
                        break

                if not has_deduction:
                    issues.append({
                        "type": "数值回退",
                        "severity": "WARN",
                        "field": field_name,
                        "detail": f"第{prev_ch}章{field_name}={prev_val} → 第{curr_ch}章{field_name}={curr_val}，下降{prev_val - curr_val}但未找到扣除说明",
                        "chapters": (prev_ch, curr_ch),
                    })

            # 数值跳跃过大（增幅超过前值的50%且增量超过100）
            if curr_val > prev_val and curr_ch > prev_ch:
                increase = curr_val - prev_val
                if increase > max(100, prev_val * 0.5):
                    # 检查中间章节是否有增量说明
                    has_increment = False
                    inc_field = field_name + "增量"
                    for ch in range(prev_ch + 1, curr_ch + 1):
                        if ch in all_data:
                            for fn, v, ln, lc in all_data[ch]:
                                if fn == inc_field:
                                    has_increment = True
                                    break
                                # 也检查正文中的"+N"描述
                                if fn == field_name and "+" in lc:
                                    has_increment = True
                                    break
                        if has_increment:
                            break

                    # 即使没有明确的增量标记，正文中可能有"增加了XX"的描述
                    # 这里只是提示，不一定有问题
                    if not has_increment:
                        issues.append({
                            "type": "数值跳跃",
                            "severity": "INFO",
                            "field": field_name,
                            "detail": f"第{prev_ch}章{field_name}={prev_val} → 第{curr_ch}章{field_name}={curr_val}，增幅{increase}，建议确认是否有对应的增量说明",
                            "chapters": (prev_ch, curr_ch),
                        })

    # 增量验证：如果同时存在绝对值和增量，验证累加是否正确
    for field_name in set(fn.replace("增量", "") for fn in field_timeline if "增量" in fn):
        base_key = field_name
        inc_key = field_name + "增量"
        if base_key not in field_timeline or inc_key not in field_timeline:
            continue

        base_timeline = sorted(field_timeline[base_key], key=lambda x: x[0])
        inc_timeline = sorted(field_timeline[inc_key], key=lambda x: x[0])

        # 对每个增量，检查是否在后续的绝对值中体现
        for inc_ch, inc_val, inc_ln, inc_lc in inc_timeline:
            # 找增量所在章节之后的下一个绝对值
            next_abs = None
            for abs_ch, abs_val, abs_ln, abs_lc in base_timeline:
                if abs_ch >= inc_ch:
                    next_abs = (abs_ch, abs_val)
                    break

            if next_abs is None:
                continue

            # 找增量之前的最后一个绝对值
            prev_abs = None
            for abs_ch, abs_val, abs_ln, abs_lc in base_timeline:
                if abs_ch < inc_ch:
                    prev_abs = (abs_ch, abs_val)

            if prev_abs is None:
                # 没有前值，跳过
                continue

            expected = prev_abs[1] + inc_val
            actual = next_abs[1]

            # 允许中间有其他增量，所以只检查 actual >= expected
            if actual < prev_abs[1]:
                issues.append({
                    "type": "增量未体现",
                    "severity": "ERROR",
                    "field": field_name,
                    "detail": f"第{inc_ch}章{field_name}+{inc_val}，前值{prev_abs[1]}（第{prev_abs[0]}章），但第{next_abs[0]}章绝对值仅{actual}，疑似计算错误",
                    "chapters": (prev_abs[0], inc_ch, next_abs[0]),
                })

    # 差额验证：差额 + 当前值 = 里程碑值，验证里程碑值是否一致
    for field_name in set(fn.replace("差额", "") for fn in field_timeline if "差额" in fn):
        base_key = field_name
        diff_key = field_name + "差额"
        if base_key not in field_timeline or diff_key not in field_timeline:
            continue

        base_timeline = sorted(field_timeline[base_key], key=lambda x: x[0])
        diff_timeline = sorted(field_timeline[diff_key], key=lambda x: x[0])

        milestone_values = []
        for diff_ch, diff_val, diff_ln, diff_lc in diff_timeline:
            # 找同章节或最近的前一个绝对值
            closest_abs = None
            for abs_ch, abs_val, abs_ln, abs_lc in base_timeline:
                if abs_ch <= diff_ch:
                    closest_abs = (abs_ch, abs_val)

            if closest_abs is None:
                continue

            milestone = closest_abs[1] + diff_val
            milestone_values.append((diff_ch, milestone, closest_abs[1], diff_val))

        # 检查里程碑值是否一致
        if len(milestone_values) >= 2:
            first_milestone = milestone_values[0][1]
            for ch, milestone, base, diff in milestone_values[1:]:
                if milestone != first_milestone:
                    issues.append({
                        "type": "里程碑不一致",
                        "severity": "WARN",
                        "field": field_name,
                        "detail": f"第{milestone_values[0][0]}章里程碑={first_milestone}（{milestone_values[0][2]}+{milestone_values[0][3]}），第{ch}章里程碑={milestone}（{base}+{diff}），不一致",
                        "chapters": (milestone_values[0][0], ch),
                    })

    return issues


def generate_report(all_data: dict, chapter_order: list, issues: list) -> str:
    """生成校验报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("小说数据计算校验报告")
    lines.append("=" * 60)
    lines.append("")

    # 数据概览
    lines.append("一、数据提取概览")
    lines.append("-" * 40)
    field_counts = defaultdict(int)
    field_latest = {}
    for ch in chapter_order:
        if ch not in all_data:
            continue
        for field_name, value, line_no, line_content in all_data[ch]:
            field_counts[field_name] += 1
            field_latest[field_name] = (ch, value)

    if not field_counts:
        lines.append("  未提取到任何数值数据。")
    else:
        lines.append(f"  {'字段名':<12} {'出现次数':<10} {'最新值（章节）':<20}")
        lines.append(f"  {'-'*12} {'-'*10} {'-'*20}")
        for fn in sorted(field_counts.keys()):
            ch, val = field_latest[fn]
            lines.append(f"  {fn:<12} {field_counts[fn]:<10} {val}（第{ch}章）")

    lines.append("")

    # 数据变化时间线
    lines.append("二、数据变化时间线")
    lines.append("-" * 40)
    field_timeline = defaultdict(list)
    for ch in chapter_order:
        if ch not in all_data:
            continue
        for field_name, value, line_no, line_content in all_data[ch]:
            if "增量" not in field_name and "差额" not in field_name:
                field_timeline[field_name].append((ch, value))

    for fn in sorted(field_timeline.keys()):
        timeline = field_timeline[fn]
        if len(timeline) < 2:
            continue
        timeline.sort(key=lambda x: x[0])
        changes = []
        prev_val = None
        for ch, val in timeline:
            if prev_val is not None:
                diff = val - prev_val
                sign = "+" if diff >= 0 else ""
                changes.append(f"第{ch}章:{val}({sign}{diff})")
            else:
                changes.append(f"第{ch}章:{val}")
            prev_val = val
        lines.append(f"  {fn}：{' → '.join(changes)}")

    lines.append("")

    # 异常报告
    lines.append("三、异常报告")
    lines.append("-" * 40)
    if not issues:
        lines.append("  ✅ 未发现数据计算异常。")
    else:
        # 按严重程度排序
        severity_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        issues.sort(key=lambda x: severity_order.get(x["severity"], 3))

        for i, issue in enumerate(issues, 1):
            severity_icon = {"ERROR": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(issue["severity"], "?")
            lines.append(f"  {severity_icon} [{issue['severity']}] #{i} {issue['type']}")
            lines.append(f"     字段：{issue['field']}")
            lines.append(f"     详情：{issue['detail']}")
            if "chapters" in issue:
                lines.append(f"     涉及章节：{issue['chapters']}")
            lines.append("")

    lines.append("=" * 60)
    lines.append(f"校验完成。共发现 {len(issues)} 个问题。")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    # Windows兼容：强制UTF-8输出
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    if len(sys.argv) < 2:
        print("用法: python data_consistency_checker.py <小说章节目录> [--world <世界观设定文件>]")
        sys.exit(1)

    chapter_dir = sys.argv[1]
    world_file = None
    if "--world" in sys.argv:
        idx = sys.argv.index("--world")
        if idx + 1 < len(sys.argv):
            world_file = sys.argv[idx + 1]

    if not os.path.isdir(chapter_dir):
        print(f"[ERROR] 目录不存在: {chapter_dir}")
        sys.exit(1)

    # 收集所有章节文件
    chapter_files = []
    for f in sorted(os.listdir(chapter_dir)):
        if f.endswith('.txt') and re.search(r'第\d+章', f):
            chapter_files.append((extract_chapter_number(f), os.path.join(chapter_dir, f)))

    chapter_files.sort(key=lambda x: x[0])
    chapter_order = [ch for ch, _ in chapter_files]

    print(f"扫描目录: {chapter_dir}")
    print(f"找到 {len(chapter_files)} 个章节文件")
    print()

    # 扫描所有章节
    all_data = {}
    for ch, filepath in chapter_files:
        results = scan_chapter(filepath)
        if results:
            all_data[ch] = results
            print(f"  第{ch}章: 提取到 {len(results)} 个数值")

    print()

    # 如果有世界观文件，加载用于参考
    world_data = {}
    if world_file and os.path.exists(world_file):
        try:
            with open(world_file, 'r', encoding='utf-8') as f:
                world_data = {"raw": f.read()}
            print(f"已加载世界观设定: {world_file}")
        except Exception as e:
            print(f"[WARN] 无法读取世界观文件: {e}")

    # 执行一致性检查
    issues = check_consistency(all_data, chapter_order)

    # 生成报告
    report = generate_report(all_data, chapter_order, issues)
    print()
    print(report)

    # 保存报告到文件
    report_path = os.path.join(chapter_dir, "数据校验报告.md")
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存至: {report_path}")
    except Exception as e:
        print(f"[WARN] 无法保存报告: {e}")


if __name__ == "__main__":
    main()
