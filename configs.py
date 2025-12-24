# werewolf_game/configs.py

# API 服务商配置
API_PROVIDERS = {
    "modelscope": {
        "api_key": "ms-7acf8090-dedc-4eae-93df-7e335ba4d466",
        "base_url": "https://api-inference.modelscope.cn/v1"
    },
    "another_provider": {
        "api_key": "YOUR_OTHER_API_KEY",
        "base_url": "https://api.another-provider.com/v1"
    }
}

# 定义我们将使用的模型ID
MODEL_LIST = {
    "deepseek": "deepseek-ai/DeepSeek-V3.2",
    "qwen": "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "MiMo" : "XiaomiMiMo/MiMo-V2-Flash",
    "dsR1" : "deepseek-ai/DeepSeek-R1-0528",
    "qwen_vl": "Qwen/Qwen3-VL-235B-A22B-Instruct" # 注意：这是一个视觉语言模型，但用于纯文本任务也兼容
}

# 游戏设置
GAME_SETUP = {
    "num_players": 9,
    "roles": {
        "werewolf": 3,
        "villager": 3,
        "seer": 1,
        "witch": 1,
        "hunter": 1
    }
}

# AI 玩家配置（8个AI + 1个用户 = 9人）
AGENT_CONFIG = [
    {
        "agent_class": "PlayerAgent",
        "model_name": "deepseek",
        "provider": "modelscope"
    },
    {
        "agent_class": "PlayerAgent",
        "model_name": "deepseek",
        "provider": "modelscope"
    },
    {
        "agent_class": "PlayerAgent",
        "model_name": "qwen",
        "provider": "modelscope"
    },
    {
        "agent_class": "PlayerAgent",
        "model_name": "qwen",
        "provider": "modelscope"
    },
    {
        "agent_class": "PlayerAgent",
        "model_name": "MiMo",
        "provider": "modelscope"
    },
    {
        "agent_class": "PlayerAgent",
        "model_name": "MiMo",
        "provider": "modelscope"
    },
    {
        "agent_class": "PlayerAgent",
        "model_name": "dsR1",
        "provider": "modelscope"
    },
    {
        "agent_class": "PlayerAgent",
        "model_name": "dsR1",
        "provider": "modelscope"
    }
]
