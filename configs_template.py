# werewolf_game/configs_template.py
# 配置文件模板 - 使用说明：
# 1. 复制此文件并重命名为 configs.py
# 2. 将下面的 YOUR_MODELSCOPE_API_KEY_HERE 替换为你的真实 API Key
# 3. configs.py 已在 .gitignore 中，不会被上传到 Git
# 
# Template Configuration File - Instructions:
# 1. Copy this file and rename it to configs.py
# 2. Replace YOUR_MODELSCOPE_API_KEY_HERE with your actual API Key
# 3. configs.py is in .gitignore and will not be uploaded to Git

# API 服务商配置
API_PROVIDERS = {
    "modelscope": {
        "api_key": "YOUR_MODELSCOPE_API_KEY_HERE",  # 🔑 在这里填入你的 ModelScope API Key
        "base_url": "https://api-inference.modelscope.cn/v1"
    },
    "another_provider": {
        "api_key": "YOUR_OTHER_API_KEY",
        "base_url": "https://api.another-provider.com/v1"
    }
}

# ====================================
# 定义我们将使用的模型ID
# ====================================
MODEL_LIST = {
    "deepseek": "deepseek-ai/DeepSeek-V3.2",
    "qwen": "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "MiMo" : "XiaomiMiMo/MiMo-V2-Flash",
    "dsR1" : "deepseek-ai/DeepSeek-R1-0528",
    "qwen_vl": "Qwen/Qwen3-VL-235B-A22B-Instruct" # 注意：这是一个视觉语言模型，但用于纯文本任务也兼容
}

# ====================================
# 游戏设置
# ====================================
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

# ====================================
# AI 玩家配置（8个AI + 1个用户 = 9人）
# ====================================
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

# ====================================
"""
1. 复制本文件并重命名为 configs.py
2. 填写你的 ModelScope API Key
3. 根据需要调整游戏配置
4. 运行 main.py 开始游戏

注意事项:
- 确保 API Key 有效且有足够的调用额度
- 如果遇到 429 错误，会自动切换到其他模型
- 日志文件会自动创建在 logs/ 目录下
- 首次运行会自动创建必要的目录
"""
