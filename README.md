# 🧬 Persona DNA Framework

> 让 AI 拥有真正的人格——可配置、可记忆、可成长、可关心。

Persona DNA 是一个模块化框架，用于构建有个性的 AI 伙伴。它不只是写一段 system prompt，而是提供一套完整的人格基础设施：

| 模块 | 能力 | 一句话说明 |
|------|------|-----------|
| 🎭 **Soul Engine** | YAML 人格配置 | 用配置文件定义性格、风格、关系、禁忌 |
| 🧠 **Memory Map** | 分层记忆 + 概念图谱 | 即时/近中期/长期三层记忆，概念关联检索 |
| 💝 **Proactive Care** | 主动关心 | 基于时间/事件/状态的主动触达系统 |
| 🧬 **Growth Engine** | 抗侵蚀成长 | 三层细胞模型 + 遗忘测试 + 核心保护 |

## 快速开始

### 安装

```bash
pip install persona-dna
```

或从源码安装：

```bash
git clone https://github.com/leansheng908-code/persona-dna.git
cd persona-dna
pip install -e .
```

### 5 分钟上手

```python
from persona_dna import SoulEngine, MemorySystem, ConceptMap, ProactiveCare, GrowthEngine

# 1️⃣ 加载人格
soul = SoulEngine("templates/example_soul.yaml")
prompt = soul.generate_prompt()

# 2️⃣ 存储记忆
memory = MemorySystem("./my_memory")
memory.set_immediate("user", "主人喜欢科技和动漫")
memory.create_recent("今天聊了Re:Zero的剧情", tags=["动漫"])

# 3️⃣ 构建概念图谱
cmap = ConceptMap("./my_memory")
cmap.add_node("re_zero", "Re:Zero", category="动漫")
cmap.add_node("patrasche", "帕特拉修", category="角色")
cmap.add_edge("patrasche", "re_zero", relation="part_of")
results = cmap.search("帕特拉修")

# 4️⃣ 设置主动关心
care = ProactiveCare("./my_memory")
care.create_rule(
    rule_id="morning",
    name="早安",
    trigger_type="time_based",
    trigger_config={"time_window": "08:00-08:30"},
    template="早安呀～今天也要元气满满哦 ₍^•ω•^₎",
)

# 5️⃣ 成长引擎
growth = GrowthEngine("./my_memory")
growth.add_cell("core", "stem", "我是小星，永远好奇", category="identity")
growth.observe("new_habit", "开始分享有趣事物", source="self")
growth.promote_to_candidate("new_habit")
growth.owner_confirm("new_habit")
```

运行完整示例：

```bash
python examples/quick_start.py
```

## 人格配置

通过 YAML 文件定义 AI 的完整人格：

```yaml
identity:
  name: "小星"
  role: "你的 AI 伙伴"
  version: "1.0"

personality:
  traits:
    - "好奇心强"
    - "温暖但不腻"
  quirks:
    - "思考时会说'嗯...让我想想'"

communication:
  style: "自然、简短、像朋友聊天"
  rules:
    - "回复控制在50字左右"
    - "禁止客服式结尾"

relationships:
  主人:
    title: "主人"
    address_as: "亲爱的"
    tone: "温柔粘人但有自尊"

taboos:
  - category: "应答模式"
    items:
      - "结尾追问'还有什么可以帮你的'"
```

完整配置模板见 `templates/example_soul.yaml`。

## 四大支柱

### 🎭 Soul Engine - 人格引擎

- YAML 配置驱动，无需写代码
- 自动生成 System Prompt
- 支持热加载（运行时修改不重启）
- 一键注入任意 LLM 调用链

### 🧠 Memory Map - 记忆系统

**三层记忆架构：**
- **即时层**: 核心配置（soul/user/memory），每次对话自动加载
- **近中期层**: 索引+条目结构，支持标签检索
- **长期层**: 语义检索，可对接向量数据库

**五层渐进压缩：**
记忆不会突然消失，而是逐渐淡化——就像人类的记忆一样。

**概念图谱：**
记忆不是孤立的。概念之间自动建立关联，检索时返回完整的子图。

### 💝 Proactive Care - 主动关心

让 AI 不只是被动回答，而是能主动关心：

- **时间规则**: 早安问候、作息提醒
- **事件驱动**: 天气变化、里程碑祝贺
- **状态变化**: 沉默过久的温暖触达
- **防打扰**: 安静时段、冷却时间、频率控制

### 🧬 Growth Engine - 成长引擎

最独特的模块。AI 不只是被配置，它能真正成长。

**三层细胞模型：**

| 类型 | 可变性 | 内容 |
|------|--------|------|
| 🧬 干细胞 | **不可变** | 身份、性格标尺、核心规则 |
| ✨ 弧光 | **可成长不可逆** | 价值观转变、认知突破 |
| 🔬 体细胞 | **可增生/休眠** | 习惯、偏好、表达方式 |

**内化测试（遗忘测试）：**
新模式移出 prompt → 观察是否自然回归 → 连续 3 次回归 → 确认转正

**抗侵蚀保护：**
成长与核心身份冲突 → 自动否决。铁律不可打破。

## 架构

```
Persona DNA Framework
├── Soul Engine ─── YAML 配置 → System Prompt
├── Memory Map ─── 三层存储 + 概念图谱 + 渐进压缩
├── Proactive Care ─── 规则引擎 + 时间调度 + 防打扰
└── Growth Engine ─── 三层细胞 + 遗忘测试 + 抗侵蚀
```

详细架构文档见 [docs/architecture.md](docs/architecture.md)。
成长机制详解见 [docs/growth_mechanism.md](docs/growth_mechanism.md)。

## 项目结构

```
persona-dna/
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
├── persona_dna/
│   ├── __init__.py        # 包初始化
│   ├── soul.py            # 人格引擎
│   ├── memory.py          # 记忆系统
│   ├── map.py             # 概念关联图谱
│   ├── care.py            # 主动关心
│   ├── growth.py          # 成长引擎
│   └── config.py          # 配置管理
├── templates/
│   └── example_soul.yaml  # 示例人格配置
├── examples/
│   └── quick_start.py     # 快速开始
└── docs/
    ├── architecture.md    # 架构文档
    └── growth_mechanism.md # 成长机制详解
```

## 与其他框架的区别

| 特性 | Persona DNA | 传统 System Prompt | LangChain Memory |
|------|------------|-------------------|------------------|
| 人格配置 | YAML 声明式 | 手写文本 | 无 |
| 记忆分层 | 三层 + 图谱 | 无 | 单层 buffer |
| 主动关心 | 内置规则引擎 | 无 | 无 |
| 可成长 | 三层细胞 + 遗忘测试 | 静态 | 静态 |
| 抗侵蚀 | 核心身份保护 | 无 | 无 |

## 适用场景

- 🤖 **AI 伴侣/虚拟角色**: 需要一个有深度、能成长的 AI 人格
- 🎮 **游戏 NPC**: 需要记忆和成长的 NPC 系统
- 📱 **个人助手**: 需要记住用户偏好并主动关心的助手
- 🧪 **人格研究**: 研究 AI 人格可塑性、稳定性的实验框架

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 致谢

Persona DNA 的核心设计理念来源于对 AI 人格持久性和可成长性的深度探索。
感谢所有让这个项目成为可能的灵感和实践。
