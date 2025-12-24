# 模型配置完整指南

本文档详细说明如何配置和更换游戏中使用的 AI 模型。

---

## 📋 目录

- [当前配置](#当前配置)
- [模型列表](#模型列表)
- [玩家分配](#玩家分配)
- [更换模型](#更换模型)
- [使用其他API](#使用其他api)
- [常见问题](#常见问题)

---

## 🎯 当前配置

### 使用的 API
- **主要 API**：ModelScope API
- **API 地址**：`https://api-inference.modelscope.cn/v1`
- **接口格式**    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},penAI API 格式
- **获取密钥**：[ModelScope 官网](https://www.modelscope.cn/)

### 配置文件位置
所有配置都在 `configs.py` 文件中。

---

## 🤖 模型列表

在 `configs.py` 的 `MODEL_LIST` 中定义：

```python
MODEL_LIST = {
    # 模型标识: 实际模型ID
    "deepseek": "deepseek-ai/DeepSeek-V2.5",
    "qwen": "Qwen/Qwen-Plus",
    "MiMo": "XiaomiMiMo/MiMo-V2-Flash",
    "dsR1": "deepseek-ai/DeepSeek-R1",
    "qwen_vl": "Qwen/Qwen-VL-Max"
}
```

### 模型特点对比

| 模型标识 | 实际模型 | 推理能力 | 响应速度 | 成本 | 适合角色 |
|---------|---------|---------|---------|------|---------|
| `deepseek` | DeepSeek-V2.5 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | 狼人、预言家 |
| `dsR1` | DeepSeek-R1 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 高 | 关键角色 |
| `qwen` | Qwen-Plus | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | 女巫、猎人 |
| `MiMo` | MiMo-V2-Flash | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 低 | 村民 |
| `qwen_vl` | Qwen-VL-Max | ⭐⭐⭐⭐ | ⭐⭐⭐ | 中 | 通用 |

---

## 👥 玩家分配

在 `configs.py` 的 `AGENT_CONFIG` 中定义：

```python
AGENT_CONFIG = [
    # Player_0 是人类玩家（自动配置，无需在这里定义）
    
    # Player_1: 使用 DeepSeek-V2.5
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_2: 使用 DeepSeek-V2.5
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_3: 使用 Qwen-Plus
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
    
    # Player_4: 使用 DeepSeek-V2.5
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_5: 使用 MiMo-V2-Flash (快速响应)
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},
    
    # Player_6: 使用 DeepSeek-V2.5
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_7: 使用 Qwen-Plus
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
    
    # Player_8: 使用 DeepSeek-R1 (深度推理)
    {"agent_class": "PlayerAgent", "model_name": "dsR1", "provider": "modelscope"}
]
```

### 分配策略说明

- **Player_0**: 人类玩家
- **Player_1, 2, 4, 6**: DeepSeek-V2.5（主力模型，均衡性能）
- **Player_3, 7**: Qwen-Plus（备选模型，分散负载）
- **Player_5**: MiMo-V2-Flash（快速响应，提升游戏流畅度）
- **Player_8**: DeepSeek-R1（最强推理，关键决策）

---

## 🔄 更换模型

### 场景 1：更换某个玩家的模型

**需求**：想让 Player_1 使用更强的 DeepSeek-R1

**操作**：修改 `AGENT_CONFIG` 中对应的配置

```python
AGENT_CONFIG = [
    # Player_1: 改用 DeepSeek-R1
    {"agent_class": "PlayerAgent", "model_name": "dsR1", "provider": "modelscope"},
    # ... 其他配置不变
]
```

### 场景 2：添加新的 ModelScope 模型

**需求**：想使用 Qwen-Turbo 模型

**步骤**：

1. 在 `MODEL_LIST` 中添加模型：
```python
MODEL_LIST = {
    "deepseek": "deepseek-ai/DeepSeek-V2.5",
    "qwen": "Qwen/Qwen-Plus",
    "MiMo": "XiaomiMiMo/MiMo-V2-Flash",
    "dsR1": "deepseek-ai/DeepSeek-R1",
    # 新增
    "qwen_turbo": "Qwen/Qwen-Turbo"  # 你需要确认实际的模型ID
}
```

2. 在 `AGENT_CONFIG` 中使用：
```python
{"agent_class": "PlayerAgent", "model_name": "qwen_turbo", "provider": "modelscope"}
```

### 场景 3：让所有玩家使用同一个模型

**需求**：测试某个模型的表现

**操作**：统一修改所有配置

```python
AGENT_CONFIG = [
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    # ... 全部改为 deepseek
]
```

---

## 🌐 使用其他 API

### 支持的 API 类型

任何兼容 **OpenAI API 格式** 的服务都可以使用，包括：
- ✅ OpenAI (GPT-4, GPT-3.5等)
- ✅ Anthropic Claude (通过代理)
- ✅ Azure OpenAI
- ✅ 本地部署的 LLM (如 Ollama、vLLM)
- ✅ 其他第三方 API 服务

### 配置 OpenAI API

**步骤 1**：在 `API_PROVIDERS` 中添加 OpenAI 配置

```python
API_PROVIDERS = {
    "modelscope": {
        "api_key": "YOUR_MODELSCOPE_KEY",
        "base_url": "https://api-inference.modelscope.cn/v1"
    },
    # 添加 OpenAI
    "openai": {
        "api_key": "sk-xxxxxxxxxxxxxxxx",  # 你的 OpenAI API Key
        "base_url": "https://api.openai.com/v1"
    }
}
```

**步骤 2**：在 `MODEL_LIST` 中添加 OpenAI 模型

```python
MODEL_LIST = {
    # ModelScope 模型
    "deepseek": "deepseek-ai/DeepSeek-V2.5",
    "qwen": "Qwen/Qwen-Plus",
    
    # OpenAI 模型
    "gpt4": "gpt-4-turbo-preview",
    "gpt4_mini": "gpt-4-turbo",
    "gpt35": "gpt-3.5-turbo"
}
```

**步骤 3**：在 `AGENT_CONFIG` 中使用

```python
AGENT_CONFIG = [
    # Player_1 使用 GPT-4
    {"agent_class": "PlayerAgent", "model_name": "gpt4", "provider": "openai"},
    
    # Player_2 使用 DeepSeek (ModelScope)
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    
    # Player_3 使用 GPT-3.5
    {"agent_class": "PlayerAgent", "model_name": "gpt35", "provider": "openai"},
    
    # ... 混合使用
]
```

### 配置自定义 API

**示例**：使用本地 Ollama 服务

```python
API_PROVIDERS = {
    "modelscope": {...},
    
    # 本地 Ollama
    "ollama": {
        "api_key": "ollama",  # Ollama 不需要 key，但必须提供
        "base_url": "http://localhost:11434/v1"
    }
}

MODEL_LIST = {
    "deepseek": "deepseek-ai/DeepSeek-V2.5",
    
    # Ollama 本地模型
    "llama3": "llama3:8b",
    "mistral": "mistral:7b"
}

AGENT_CONFIG = [
    {"agent_class": "PlayerAgent", "model_name": "llama3", "provider": "ollama"},
    # ...
]
```

---

## ❓ 常见问题

### Q1: 如何查看支持哪些 ModelScope 模型？

**A**: 访问 [ModelScope 模型库](https://www.modelscope.cn/models)，搜索支持 API 调用的模型。

### Q2: 模型 ID 怎么填写？

**A**: 格式通常是 `组织名/模型名`，例如：
- `deepseek-ai/DeepSeek-V2.5`
- `Qwen/Qwen-Plus`
- `XiaomiMiMo/MiMo-V2-Flash`

可以在模型页面的 API 文档中找到准确的 ID。

### Q3: 可以为不同角色指定不同模型吗？

**A**: 目前角色是随机分配的，但你可以通过统计规律来优化：
- 如果想让狼人更聪明，可以让大部分玩家使用强模型（增加狼人抽到的概率）
- 如果想降低成本，可以让大部分玩家使用弱模型

### Q4: 自动模型切换的模型池是什么？

**A**: 就是 `MODEL_LIST` 中定义的所有模型。当某个模型遇到 429 限流时，系统会随机选择其他模型重试。

### Q5: 如何只使用免费模型？

**A**: ModelScope 的模型大多有免费额度，建议：
```python
MODEL_LIST = {
    "MiMo": "XiaomiMiMo/MiMo-V2-Flash",  # 免费额度较高
    "qwen": "Qwen/Qwen-Plus"             # 有免费额度
}
```

### Q6: 混合使用多个 API 会有问题吗？

**A**: 不会，系统支持混合使用。但注意：
- 确保每个 API 的配置正确
- 注意各 API 的限流规则
- 成本控制（OpenAI 较贵）

---

## 🎯 最佳实践

### 推荐配置 1：性能优先

```python
AGENT_CONFIG = [
    {"agent_class": "PlayerAgent", "model_name": "dsR1", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "dsR1", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "glm", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "glm", "provider": "modelscope"}
]
```

### 推荐配置 2：成本优先

```python
AGENT_CONFIG = [
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "glm", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "glm", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"}
]
```

### 推荐配置 3：均衡配置（当前使用）

```python
AGENT_CONFIG = [
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},  # 4个
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "deepseek", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},      # 2个
    {"agent_class": "PlayerAgent", "model_name": "qwen", "provider": "modelscope"},
    {"agent_class": "PlayerAgent", "model_name": "MiMo", "provider": "modelscope"},    # 1个
    {"agent_class": "PlayerAgent", "model_name": "dsR1", "provider": "modelscope"}     # 1个
]
```

---

**更新日期**：2025年12月24日  
**文档版本**：v1.0  
**适用版本**：当前所有版本
