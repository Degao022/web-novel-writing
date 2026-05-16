#!/usr/bin/env python3
"""
网络小说大纲生成器
用法：python outline_generator.py
交互式输入书名、流派、核心设定，自动生成分章大纲框架
"""

import json
import sys

# 各流派的大纲模板
GENRE_TEMPLATES = {
    "玄幻修仙": {
        "power_system": ["炼气期", "筑基期", "金丹期", "元婴期", "化神期", "大乘期", "渡劫期"],
        "opening_types": ["废柴逆袭", "穿越带系统", "重生复仇", "血脉觉醒"],
        "volume_themes": [
            "初入修炼路，逆境显天赋",
            "离家闯荡，横扫天才",
            "秘境历练，获取传承",
            "势力纷争，确立地位",
            "域外征战，打破天花板",
            "问鼎天下，成就至强"
        ]
    },
    "都市异能": {
        "power_system": ["初阶觉醒", "C级异能者", "B级异能者", "A级异能者", "S级异能者", "SSS级"],
        "opening_types": ["退伍归来", "重生大佬", "赘婿逆袭", "普通觉醒"],
        "volume_themes": [
            "归来/觉醒，第一次打脸",
            "扩大圈子，掌控局面",
            "商界/政界布局",
            "幕后大佬现身，危机升级",
            "全面反击，清算旧账"
        ]
    },
    "古言权谋": {
        "power_system": ["白身", "秀才/举人", "进士/官员", "六部尚书", "宰相/王侯", "皇权"],
        "opening_types": ["现代穿越", "重生悲剧收场", "庶女崛起", "落魄书生"],
        "volume_themes": [
            "初入局，摸清势力格局",
            "站队表态，第一次政治胜利",
            "感情线铺开，内外双线并进",
            "最大危机，几乎满盘皆输",
            "反转局势，清算所有敌人",
            "圆满收尾"
        ]
    },
    "星际科幻": {
        "power_system": ["新兵/平民", "士官/工程师", "军官/科学家", "将领/院士", "舰队司令", "银河霸主"],
        "opening_types": ["落魄天才觉醒", "穿越到未来", "末世废墟崛起", "机甲驾驶员觉醒"],
        "volume_themes": [
            "初出茅庐，崭露锋芒",
            "第一次大战，一战成名",
            "卷入政治漩涡",
            "星际大战爆发，全面参战",
            "终极决战，扭转星际格局"
        ]
    },
    "言情甜宠": {
        "power_system": ["普通人", "小有成就", "业界知名", "顶流/豪门"],
        "opening_types": ["邂逅型", "青梅竹马型", "欢喜冤家型", "契约婚姻型"],
        "volume_themes": [
            "相遇，互有印象",
            "相处，暗生情愫",
            "误会/阻碍，虐恋期",
            "真相大白，和解",
            "携手，HE收场"
        ]
    }
}


def get_input(prompt, default=None):
    """获取用户输入，支持默认值"""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


def generate_chapter_outline(genre_data, total_chapters, volumes):
    """生成分章大纲框架"""
    chapters_per_volume = total_chapters // len(volumes)
    outline = []
    
    chapter_num = 1
    for vol_idx, vol_theme in enumerate(volumes):
        vol_start = chapter_num
        vol_end = min(chapter_num + chapters_per_volume - 1, total_chapters)
        
        # 每卷分为三段
        seg1_end = vol_start + (vol_end - vol_start) // 3
        seg2_end = vol_start + 2 * (vol_end - vol_start) // 3
        
        outline.append({
            "volume": vol_idx + 1,
            "title": f"第{vol_idx + 1}卷：{vol_theme}",
            "chapters": f"第{vol_start}-{vol_end}章",
            "segments": [
                {
                    "range": f"第{vol_start}-{seg1_end}章",
                    "phase": "铺垫蓄力",
                    "events": [
                        "引入本卷主要矛盾",
                        "主角当前实力/状态展示",
                        "第一个小爽点（约第" + str(vol_start + 10) + "章）"
                    ]
                },
                {
                    "range": f"第{seg1_end + 1}-{seg2_end}章",
                    "phase": "矛盾激化",
                    "events": [
                        "反派/阻碍势力登场",
                        "主角遭遇挫折或压力",
                        "中期小高潮（打脸/突破）"
                    ]
                },
                {
                    "range": f"第{seg2_end + 1}-{vol_end}章",
                    "phase": "高潮爆发",
                    "events": [
                        "主角至暗时刻",
                        "力量爆发/转机出现",
                        "彻底解决本卷矛盾",
                        "埋下下一卷伏笔"
                    ]
                }
            ]
        })
        chapter_num = vol_end + 1
    
    return outline


def format_outline_text(title, genre, protagonist, antagonist, gold_finger, power_system, outline):
    """格式化输出大纲文本"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  《{title}》 大纲框架")
    lines.append("=" * 60)
    lines.append("")
    lines.append("【基础设定】")
    lines.append(f"流派：{genre}")
    lines.append(f"主角：{protagonist}")
    lines.append(f"核心金手指/外挂：{gold_finger}")
    lines.append(f"主要反派：{antagonist}")
    lines.append("")
    lines.append("【力量体系】")
    for i, level in enumerate(power_system):
        lines.append(f"  {'★' * min(i+1, 5)} {level}")
    lines.append("")
    lines.append("【分卷大纲】")
    lines.append("")
    
    for vol in outline:
        lines.append(f"{'─' * 50}")
        lines.append(f"  {vol['title']}")
        lines.append(f"  章节范围：{vol['chapters']}")
        lines.append("")
        
        for seg in vol['segments']:
            lines.append(f"  [{seg['phase']}] {seg['range']}")
            for event in seg['events']:
                lines.append(f"    · {event}")
            lines.append("")
    
    lines.append("=" * 60)
    lines.append("提示：以上为大纲框架，请根据实际创作进行细化。")
    lines.append("每个段落建议细化到每10章一个具体事件。")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main():
    print("\n" + "=" * 60)
    print("  网络小说大纲生成器")
    print("=" * 60)
    print()
    
    # 选择流派
    genres = list(GENRE_TEMPLATES.keys())
    print("支持的流派：")
    for i, g in enumerate(genres, 1):
        print(f"  {i}. {g}")
    
    while True:
        choice = get_input("请选择流派编号")
        if choice.isdigit() and 1 <= int(choice) <= len(genres):
            genre = genres[int(choice) - 1]
            break
        print("输入无效，请重新选择")
    
    genre_data = GENRE_TEMPLATES[genre]
    
    print(f"\n已选择：{genre}")
    print()
    
    # 基础信息
    title = get_input("书名", "待定")
    
    # 开局类型
    print(f"\n常见开局类型（{genre}）：")
    for i, ot in enumerate(genre_data["opening_types"], 1):
        print(f"  {i}. {ot}")
    opening_choice = get_input("选择开局类型编号（或直接输入自定义开局）", "1")
    if opening_choice.isdigit() and 1 <= int(opening_choice) <= len(genre_data["opening_types"]):
        opening = genre_data["opening_types"][int(opening_choice) - 1]
    else:
        opening = opening_choice
    
    protagonist = get_input("主角名字及简单描述（如：林枫，寒门子弟，性格坚韧）", "主角（待定）")
    gold_finger = get_input("金手指/核心外挂（如：万倍返还系统、上古传承、重生记忆）", "待定")
    antagonist = get_input("主要反派/对立势力", "待定")
    
    # 力量体系
    print(f"\n默认力量体系（{genre}）：")
    default_system = genre_data["power_system"]
    print("  " + " → ".join(default_system))
    custom = get_input("是否使用默认体系？(y/n)", "y")
    
    if custom.lower() == 'n':
        print("请输入自定义境界/等级（用逗号分隔，从低到高）：")
        custom_input = get_input("境界列表")
        power_system = [s.strip() for s in custom_input.split("，") if s.strip()]
        if not power_system:
            power_system = [s.strip() for s in custom_input.split(",") if s.strip()]
        if not power_system:
            power_system = default_system
    else:
        power_system = default_system
    
    # 全书章数
    total_str = get_input("预计总章数", "500")
    try:
        total_chapters = int(total_str)
    except ValueError:
        total_chapters = 500
    
    # 卷数
    vol_count_str = get_input("分卷数量", str(len(genre_data["volume_themes"])))
    try:
        vol_count = int(vol_count_str)
    except ValueError:
        vol_count = len(genre_data["volume_themes"])
    
    # 卷主题
    volumes = genre_data["volume_themes"][:vol_count]
    if len(volumes) < vol_count:
        print(f"\n默认只有{len(genre_data['volume_themes'])}个卷主题，请补充剩余{vol_count - len(volumes)}个：")
        while len(volumes) < vol_count:
            theme = get_input(f"第{len(volumes) + 1}卷主题")
            volumes.append(theme)
    
    # 生成大纲
    outline = generate_chapter_outline(genre_data, total_chapters, volumes)
    
    # 附加开局信息
    if outline:
        outline[0]['opening'] = opening
    
    result_text = format_outline_text(title, genre, protagonist, antagonist, gold_finger, power_system, outline)
    
    print("\n" + result_text)
    
    # 保存到文件
    save = get_input("\n是否保存大纲到文件？(y/n)", "y")
    if save.lower() == 'y':
        filename = f"{title}_大纲框架.txt" if title != "待定" else "novel_outline.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result_text)
        print(f"已保存到：{filename}")
    
    print("\n大纲生成完成！可根据此框架进行细化创作。")


if __name__ == "__main__":
    main()
