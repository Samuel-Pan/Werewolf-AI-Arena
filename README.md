# 🐺 AI 狼人杀多智能体游戏

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![AgentScope](https://img.shields.io/badge/AgentScope-Latest-green.svg)](https://github.com/modelscope/agentscope)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于 AgentScope 框架的多智能体狼人杀游戏系统，支持 1 位人类玩家与 8 位 AI 玩家进行实时对战。

</div>

---
## 🎮 游戏截图
在cmd命令中运行：
<img width="1920" height="1020" alt="94669b218269d4eecff7b302db6ede86" src="https://github.com/user-attachments/assets/981668f7-3288-48ae-921b-1e037d9dee92" />
<img width="1920" height="1020" alt="86ab4bbddebbc07cbe6f36fb2f79022b" src="https://github.com/user-attachments/assets/b7b12c46-6873-4da5-9f3a-e57ea8caef9a" />

## 🎮 游戏配置

### 当前配置：9人标准局
- **1 位人类玩家** + **8 位 AI 玩家**
- **角色分配**：
  - 🐺 狼人 × 3：夜晚击杀一名玩家，团队协作
  - 🔮 预言家 × 1：每晚查验一名玩家身份（好人/狼人）
  - 💊 女巫 × 1：拥有一瓶解药（救人）和一瓶毒药（杀人），各用一次
  - 🏹 猎人 × 1：被淘汰时可开枪带走一人（被毒除外）
  - 👤 村民 × 3：推理分析，投票找狼

### 如何调整人数和角色？

编辑 `configs.py` 文件：

```python
GAME_SETUP = {
    "num_players": 9,  # 修改总人数（包含1位人类玩家）
    "roles": {
        "werewolf": 3,   # 狼人数量
        "villager": 3,   # 村民数量
        "seer": 1,       # 预言家数量
        "witch": 1,      # 女巫数量
        "hunter": 1,     # 猎人数量
        "guard": 1       # 可添加新角色（需实现逻辑）
    }
}

# 同时调整 AI 玩家配置（数量 = num_players - 1）
AGENT_CONFIG = [
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "glm", "provider": "modelscope"},
    # ... 继续添加到总人数-1
]
```

> ⚠️ **注意**：修改人数后，需确保 `AGENT_CONFIG` 列表长度 = `num_players - 1`

---

## 🏗️ 系统架构

```
                    Game Master (裁判)
                    游戏流程控制 + AI 模型管理
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
    Public Hub        Werewolf Hub        AI Models Pool
    (公开频道)        (狼人私密频道)      (自动切换)
         │                  │                  │
         │                  │            DeepSeek / Qwen
         │                  │            MiMo / dsR1 ...
         │                  │
         ├─── Player_0 (Human) ──── UserAgent
         │
         ├─── Player_1 (AI) ──────── ReActAgent
         ├─── Player_2 (AI) ──────── ReActAgent
         ├─── Player_3 (AI) ──────── ReActAgent
         ├─── ... (共 8 个 AI)
         └─── Player_8 (AI) ──────── ReActAgent
```

### 核心组件

| 组件 | 功能 |
|------|------|
| **Game Master** | 游戏流程控制、状态管理、胜负判定、记忆摘要生成 |
| **Public Hub** | 所有玩家的公开发言频道 |
| **Werewolf Hub** | 狼人阵营的私密聊天频道 |
| **UserAgent** | 人类玩家交互接口 |
| **ReActAgent** | AI 玩家（推理-行动模式） |
| **日志系统** | game_log（游戏流程）+ prompt_log（AI 交互）|

---

## 🚀 快速开始

### 前置要求
- Python 3.10+
- ModelScope API Key（[免费获取](https://modelscope.cn/my/myaccesstoken)）

### 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/Samuel-Pan/Werewolf-AI-Arena.git
cd werewolf-multiagent-game
```

#### 2. 安装依赖
```bash
pip install agentscope
```

#### 3. 配置 API Key ⚠️ 重要

```bash
# 复制配置模板
Copy-Item configs_template.py configs.py
```

打开 `configs.py`，将 `YOUR_MODELSCOPE_API_KEY_HERE` 替换为你的真实 API Key：

```python
API_PROVIDERS = {
    "modelscope": {
        "api_key": "你的_API_KEY_这里",  # 🔑 替换这里
        "base_url": "https://api-inference.modelscope.cn/v1"
    }
}
```

> 💡 **获取 API Key**：访问 [ModelScope 控制台](https://modelscope.cn/my/myaccesstoken) 免费获取

#### 4. 启动游戏
```bash
python main.py
```

---

## 🤖 模型配置说明

### 当前使用的 API 和模型

本项目使用 **ModelScope API**，使用了以下模型：

| 模型标识 | 实际模型 | 特点 |
|---------|---------|------|
| `deepseek` | DeepSeek-V2.5 | 推理能力强，适合复杂逻辑 |
| `qwen` | Qwen-Plus | 均衡性能，通用性好 |
| `MiMo` | MiMo-V2-Flash | 快速响应 |
| `dsR1` | DeepSeek-R1 | 深度推理模型 |

### AI 玩家模型分配

在 `configs.py` 中的 `AGENT_CONFIG` 定义了每个 AI 玩家使用的模型：

```python
AGENT_CONFIG = [
    # Player_1 使用 DeepSeek
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_2 使用 DeepSeek
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_3 使用 Qwen
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
    
    # Player_4 使用 DeepSeek
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_5 使用 MiMo
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},
    
    # Player_6 使用 DeepSeek
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_7 使用 Qwen
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
    
    # Player_8 使用 DeepSeek-R1
    {"agent_class": "PlayerAgent", "model_name": "dsR1", "provider": "modelscope"}
]
```

> 💡 **提示**：Player_0 是人类玩家，Player_1 到 Player_8 是 AI 玩家

### 如何更换模型？

#### 方法 1：使用 ModelScope 的其他模型

1. 在 `configs.py` 的 `MODEL_LIST` 中添加新模型：

```python
MODEL_LIST = {
    "deepseek": "deepseek-ai/DeepSeek-V2.5",
    "glm": "Qwen/Qwen-Plus",
    "MiMo": "XiaomiMiMo/MiMo-V2-Flash",
    "dsR1": "deepseek-ai/DeepSeek-R1",
    # 添加新模型
    "qwen_turbo": "Qwen/Qwen-Turbo",
    "baichuan": "baichuan-inc/Baichuan2-13B-Chat"
}
```

2. 在 `AGENT_CONFIG` 中使用新模型：

```python
{"agent_class": "PlayerAgent", "model_name": "qwen_turbo", "provider": "modelscope"}
```

#### 方法 2：使用其他 API（如 OpenAI、Claude 等）

1. 在 `configs.py` 中添加新的 API 配置：

```python
API_PROVIDERS = {
    "modelscope": {
        "api_key": "YOUR_MODELSCOPE_KEY",
        "base_url": "https://api-inference.modelscope.cn/v1"
    },
    # 添加 OpenAI
    "openai": {
        "api_key": "YOUR_OPENAI_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    # 添加其他兼容 OpenAI 格式的 API
    "custom": {
        "api_key": "YOUR_CUSTOM_KEY",
        "base_url": "https://your-api-endpoint.com/v1"
    }
}
```

2. 在 `MODEL_LIST` 中添加对应模型：

```python
MODEL_LIST = {
    # ModelScope 模型
    "deepseek": "deepseek-ai/DeepSeek-V2.5",
    "qwen": "Qwen/Qwen-Plus",
    
    # OpenAI 模型
    "gpt4": "gpt-4-turbo",
    "gpt35": "gpt-3.5-turbo",
    
    # 其他 API 的模型
    "custom_model": "your-model-name"
}
```

3. 在 `AGENT_CONFIG` 中指定使用的 provider：

```python
AGENT_CONFIG = [
    # 使用 ModelScope
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # 使用 OpenAI
    {"agent_class": "PlayerAgent", "model_name": "gpt4", "provider": "openai"},
    
    # 使用自定义 API
    {"agent_class": "PlayerAgent", "model_name": "custom_model", "provider": "custom"},
    
    # 混合使用
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
]
```

### 模型性能建议

| 场景 | 推荐模型 | 说明 |
|------|---------|------|
| **推理能力** | DeepSeek-R1, GPT-4 | 适合预言家、狼人等需要策略的角色 |
| **快速响应** | MiMo, GPT-3.5 | 适合村民等普通角色 |
| **成本控制** | Qwen-Plus, MiMo | ModelScope 免费额度较高 |
| **混合配置** | 关键角色用强模型 | 预言家用 DeepSeek-R1，村民用 MiMo |

---

## � 游戏流程

```
【第 N 天开始】
    │
    ├─ 🌙 夜晚阶段
    │   ├─ 狼人击杀
    │   ├─ 预言家查验
    │   └─ 女巫用药
    │
    ├─ 🌅 公布结果
    │   ├─ 遗言环节
    │   └─ 猎人开枪（如适用）
    │
    ├─ 💬 白天讨论
    │   └─ 所有玩家依次发言
    │
    ├─ 🗳️ 投票环节
    │   ├─ 投票淘汰一人
    │   ├─ 遗言
    │   └─ 猎人开枪（如适用）
    │
    └─ 🏆 胜负判定
        ├─ 好人胜：狼人全灭
        ├─ 狼人胜：狼人数 ≥ 好人数
        └─ 继续下一天
```

---

## ⚙️ 核心特性

### 1. 智能记忆系统
AI 会记住游戏历程，每天生成个性化记忆摘要：
- 历史事件整合
- 角色行为分析
- 策略性决策支持

### 2. 自动模型切换
遇到 API 限流（429错误）时：
1. 自动检测当前模型
2. 从模型池随机选择其他模型
3. 最多重试 3 次
4. 记录切换日志

配置模型池（`configs.py`）：
```python
MODEL_LIST = {
    "deepseek": "deepseek-ai/DeepSeek-V3.2",
    "qwen": "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "MiMo": "XiaomiMiMo/MiMo-V2-Flash",
    "dsR1": "deepseek-ai/DeepSeek-R1-0528"
}
```

### 3. 双日志系统
- **game_log**：游戏流程、玩家发言、角色身份（上帝视角）
- **prompt_log**：所有 AI Prompt 记录（调试用）

---

## � 人类玩家操作指南

### 输入格式
- 玩家编号：`Player_2` 或 `2` 或 `player2`（不区分大小写）
- 确认操作：`y` / `yes` / `n` / `no`

### 各角色操作

| 角色 | 夜晚行动 | 白天行动 | 特殊说明 |
|------|---------|---------|---------|
| � **狼人** | 输入击杀目标编号 | 发言伪装 + 投票 | 可查看狼人私聊 |
| 🔮 **预言家** | 输入查验目标编号 | 公布查验结果 + 投票 | 引导好人投票 |
| 💊 **女巫** | 解药/毒药选择 | 隐藏身份 + 投票 | 同一夜不能同时用药 |
| 🏹 **猎人** | - | 发言威慑 + 投票 | 被淘汰时可开枪（被毒除外）|
| 👤 **村民** | - | 逻辑推理 + 投票 | 分析发言找狼 |

---

## ❓ 常见问题

**Q: 找不到 configs.py 文件？**  
A: `configs.py` 是从 `configs_template.py` 复制并配置的。运行 `Copy-Item configs_template.py configs.py`，然后编辑填入你的 API Key。

**Q: 如何获取 ModelScope API Key？**  
A: 访问 [ModelScope 控制台](https://modelscope.cn/my/myaccesstoken) 免费获取。ModelScope 提供免费额度，足够正常使用。

**Q: 如何增加游戏人数？**  
A: 修改 `configs.py` 中的 `GAME_SETUP["num_players"]` 和角色配置，同时调整 `AGENT_CONFIG` 数量。

**Q: 遇到 API 限流怎么办？**  
A: 系统会自动切换模型重试（最多3次），建议在 `MODEL_LIST` 中配置多个模型。

**Q: 如何更换 AI 模型？**  
A: 在 `configs.py` 的 `AGENT_CONFIG` 中修改 `model_name`。

**Q: 日志文件在哪里？**  
A: `logs/` 目录下，文件名包含时间戳（如 `game_20231223_143022.log`）。

**Q: 如何添加新角色？**  
A: 1) 在 `prompts/` 创建角色提示词文件；2) 在 `configs.py` 添加角色配置；3) 在 `game_master.py` 实现角色逻辑。

---

## 📂 项目结构

```
werewolf_game/
├── agents/                  # 智能体定义
│   ├── game_master.py      # 裁判（核心逻辑）
│   ├── player_agent.py     # AI 玩家工厂
│   └── user_agent.py       # 人类玩家
├── prompts/                 # 角色系统提示词
│   ├── werewolf.txt
│   ├── seer.txt
│   └── ...
├── logs/                    # 日志目录
├── configs.py               # 游戏配置
├── logger.py                # 日志系统
├── main.py                  # 游戏入口
└── requirements.txt         # 依赖列表
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## � 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

<div align="center">

**⭐ 如果觉得有帮助，请给个 Star！⭐**

</div>
