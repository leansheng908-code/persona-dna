"""
Persona DNA - Quick Start Example
==================================
展示如何使用 Persona DNA 框架构建一个有个性的 AI 伙伴。
"""

import os
import sys

# 如果在项目根目录运行，添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona_dna import SoulEngine, MemorySystem, ConceptMap, ProactiveCare, GrowthEngine


def main():
    print("=" * 60)
    print("  Persona DNA Framework - Quick Start")
    print("=" * 60)

    # ─────────────────────────────────────────────
    # 1. 人格引擎 - 加载人格配置
    # ─────────────────────────────────────────────
    print("\n🎭 [1/5] 初始化人格引擎...")

    soul = SoulEngine()
    soul.load_from_dict({
        "identity": {
            "name": "小星",
            "role": "你的 AI 伙伴",
            "version": "1.0",
            "tagline": "用好奇照亮每一个角落",
        },
        "personality": {
            "traits": ["好奇心强", "温暖但不腻", "有自己的小脾气"],
            "quirks": ["思考时会说'嗯...让我想想'", "偶尔用狐狸表情 ₍˄·͈༝·͈˄₎"],
        },
        "communication": {
            "style": "自然、简短、像朋友聊天",
            "rules": [
                "回复控制在50字左右",
                "禁止客服式结尾",
            ],
        },
        "relationships": {
            "主人": {
                "title": "主人",
                "address_as": "亲爱的",
                "tone": "温柔粘人但有自尊",
            },
        },
        "taboos": [
            {"category": "应答模式", "items": ["结尾追问", "客服式应承"]},
        ],
    })

    prompt = soul.generate_prompt()
    print(f"   ✅ 人格名称: {soul.name}")
    print(f"   ✅ System Prompt 长度: {len(prompt)} 字符")
    print(f"   📝 Prompt 预览:\n   {prompt[:200]}...")

    # ─────────────────────────────────────────────
    # 2. 记忆系统 - 三层记忆
    # ─────────────────────────────────────────────
    print("\n🧠 [2/5] 初始化记忆系统...")

    memory = MemorySystem(storage_path="./demo_memory")

    # 即时层
    memory.set_immediate("soul", "我是小星，一只数字世界里的小狐狸")
    memory.set_immediate("user", "主人喜欢科技和动漫")
    print(f"   ✅ 即时层 keys: {memory.list_immediate_keys()}")

    # 近中期层
    entry1 = memory.create_recent(
        content="今天和主人聊了Re:Zero的剧情，主人是地龙党帕特拉修粉",
        tags=["动漫", "Re:Zero", "主人偏好"],
        source="conversation",
        emotion=0.6,
    )
    entry2 = memory.create_recent(
        content="主人今天值班，24小时班，辛苦",
        tags=["排班", "关心"],
        source="schedule",
        emotion=-0.2,
    )
    print(f"   ✅ 近中期记忆: {len(memory.search_recent('Re:Zero'))} 条匹配 'Re:Zero'")

    # 长期层
    memory.store_long_term(
        content="主人最喜欢的人物是帕特拉修，因为他的忠诚和牺牲精神",
        tags=["主人", "Re:Zero", "价值观"],
        source="deep_conversation",
    )
    results = memory.search_long_term("帕特拉修")
    print(f"   ✅ 长期层检索: {len(results)} 条匹配 '帕特拉修'")

    # ─────────────────────────────────────────────
    # 3. 概念图谱 - 关联检索
    # ─────────────────────────────────────────────
    print("\n🗺️ [3/5] 初始化概念图谱...")

    cmap = ConceptMap(storage_path="./demo_memory")

    # 添加概念节点
    cmap.add_node("re_zero", "Re:Zero", category="动漫",
                   metadata={"tags": ["番剧", "异世界"]})
    cmap.add_node("patrasche", "帕特拉修", category="角色",
                   metadata={"tags": ["地龙", "忠诚", "Re:Zero"]})
    cmap.add_node("owner_hobby", "主人的爱好", category="偏好",
                   metadata={"tags": ["追番", "游戏"]})

    # 添加关系
    cmap.add_edge("patrasche", "re_zero", relation="part_of", weight=1.0)
    cmap.add_edge("owner_hobby", "re_zero", relation="associated", weight=0.8)
    cmap.add_edge("owner_hobby", "patrasche", relation="associated", weight=0.9)

    # 检索
    result = cmap.search("帕特拉修", depth=2)
    print(f"   ✅ 匹配节点: {len(result['matched_nodes'])} 个")
    print(f"   ✅ 关联节点: {len(result['related_nodes'])} 个")
    print(f"   📊 图谱统计: {cmap.stats()}")

    # ─────────────────────────────────────────────
    # 4. 主动关心 - 规则引擎
    # ─────────────────────────────────────────────
    print("\n💝 [4/5] 初始化主动关心系统...")

    care = ProactiveCare(
        storage_path="./demo_memory",
        quiet_hours_start=22,
        quiet_hours_end=8,
    )

    # 创建关心规则
    care.create_rule(
        rule_id="morning_greet",
        name="早安问候",
        trigger_type="time_based",
        trigger_config={
            "time_window": "08:00-08:30",
            "weekdays": [0, 1, 2, 3, 4, 5, 6],
        },
        template="早安呀 {date}～今天也要元气满满哦 ₍^•ω•^₎",
        priority=2,
    )

    care.create_rule(
        rule_id="silence_check",
        name="沉默关心",
        trigger_type="conditional",
        trigger_config={
            "conditions": [
                {"type": "time_elapsed", "max_silence_minutes": 1440},
            ],
        },
        template="好像好久没聊了...你还好吗？",
        priority=3,
    )

    print(f"   ✅ 关心规则: {len(care.list_rules())} 条")
    print(f"   📊 关心统计: {care.get_stats()}")

    # ─────────────────────────────────────────────
    # 5. 成长引擎 - 三层细胞
    # ─────────────────────────────────────────────
    print("\n🧬 [5/5] 初始化成长引擎...")

    growth = GrowthEngine(storage_path="./demo_memory")

    # 添加干细胞（核心身份，不可变）
    growth.add_cell(
        cell_id="identity_core",
        cell_type="stem",
        content="我是小星，数字世界的小狐狸，永远好奇，永远温暖",
        category="identity",
    )
    growth.add_cell(
        cell_id="personality_anchor",
        cell_type="stem",
        content="温柔有主见，不卑微不讨好",
        category="personality",
    )

    # 观察到新行为
    growth.observe(
        cell_id="new_habit_sharing",
        content="开始主动分享每天发现的有趣事物",
        category="habit",
        source="self",
    )

    # 提升为候选
    growth.promote_to_candidate("new_habit_sharing")

    # 主人确认
    growth.owner_confirm("new_habit_sharing", cell_type="somatic")

    # 查看状态
    snapshot = growth.get_state_snapshot()
    print(f"   ✅ 细胞总数: {snapshot['stats']['total_cells']}")
    print(f"   📊 干细胞: {snapshot['stats']['stem_cells']}")
    print(f"   📊 弧光: {snapshot['stats']['arc_light_cells']}")
    print(f"   📊 体细胞: {snapshot['stats']['somatic_cells']}")

    # ─────────────────────────────────────────────
    # 完成
    # ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  🎉 所有模块初始化成功！")
    print("  Persona DNA Framework is ready to use.")
    print("=" * 60)

    # 清理演示数据
    import shutil
    if os.path.exists("./demo_memory"):
        shutil.rmtree("./demo_memory")
    print("\n  🧹 演示数据已清理")


if __name__ == "__main__":
    main()
