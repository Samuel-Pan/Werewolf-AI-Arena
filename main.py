# werewolf_game/main.py

import asyncio
import random
from agentscope.message import Msg
from configs import API_PROVIDERS, MODEL_LIST, GAME_SETUP, AGENT_CONFIG
from agents.player_agent import create_player_agent
from agents.user_agent import create_user_agent
from agents.game_master import GameMasterAgent
from agentscope.model import OpenAIChatModel

# 角色中英文映射
ROLE_CN_MAP = {
    "werewolf": "狼人",
    "seer": "预言家",
    "witch": "女巫",
    "hunter": "猎人",
    "villager": "村民"
}

async def setup_and_run_game():
    """封装一局游戏的设置和运行"""
    print("\n\n===== 正在准备新的一局游戏... =====")

    # 从 GAME_SETUP 生成角色列表
    ROLES = []
    for role, count in GAME_SETUP["roles"].items():
        ROLES.extend([role] * count)
    
    if len(ROLES) != GAME_SETUP["num_players"]:
        print(f"错误：configs.py 中定义的角色数量 ({len(ROLES)}) 与玩家数量 ({GAME_SETUP['num_players']}) 不匹配！")
        return
        
    random.shuffle(ROLES)

    players = []
    player_identities = {}
    
    # 1. 创建人类玩家并分配角色
    user_role = ROLES.pop(0)
    user_agent = create_user_agent()
    # 【重要】为UserAgent添加特殊标记
    setattr(user_agent, 'is_user', True)
    user_agent.name = "Player_0"
    setattr(user_agent, 'role', user_role)
    players.append(user_agent)
    player_identities[user_agent.name] = user_role
    print(f"你的身份是: 【{ROLE_CN_MAP.get(user_role, user_role)}】")

    # 2. 创建AI玩家并分配角色
    for i, role in enumerate(ROLES):
        player_id = i + 1
        agent_config = AGENT_CONFIG[i]
        provider_config = API_PROVIDERS[agent_config["provider"]]
        model_config = {
            "model_name": MODEL_LIST[agent_config["model_name"]],
            "api_key": provider_config["api_key"],
            "base_url": provider_config["base_url"],
        }
        
        ai_agent = create_player_agent(
            role=role, model_config=model_config, agent_id=player_id
        )
        ai_agent.name = f"Player_{player_id}"
        setattr(ai_agent, 'role', role)
        setattr(ai_agent, 'is_user', False)
        players.append(ai_agent)
        player_identities[ai_agent.name] = role

    # 3. 创建裁判Agent
    # 裁判主模型使用 qwen_vl（功能强大，用于裁判逻辑）
    qwen_provider_config = API_PROVIDERS["modelscope"]
    qwen_config = {
        "model_name": MODEL_LIST["qwen_vl"],
        "api_key": qwen_provider_config["api_key"],
        "base_url": qwen_provider_config["base_url"],
    }
    qwen_model = OpenAIChatModel(
        model_name=qwen_config["model_name"],
        api_key=qwen_config["api_key"],
        client_args={"base_url": qwen_config["base_url"]},
    )
    
    # 创建专门用于生成记忆摘要的轻量级模型（deepseek）
    summary_provider_config = API_PROVIDERS["modelscope"]
    summary_config = {
        # "model_name": MODEL_LIST["deepseek"],
        "model_name": MODEL_LIST["qwen_vl"],
        "api_key": summary_provider_config["api_key"],
        "base_url": summary_provider_config["base_url"],
    }
    summary_model = OpenAIChatModel(
        model_name=summary_config["model_name"],
        api_key=summary_config["api_key"],
        client_args={"base_url": summary_config["base_url"]},
    )
    
    game_master = GameMasterAgent(
        players=players, 
        player_identities=player_identities, 
        model=qwen_model,
        summary_model=summary_model  # 传入专门的摘要模型
    )

    # 4. 在游戏开始前，向所有狼人（包括AI）通知队友
    await game_master.notify_werewolves_of_teammates()

    # 5. 启动游戏
    try:
        await game_master.run_game()
    except Exception as e:
        print(f"\n游戏运行出现异常: {e}")
        import traceback
        traceback.print_exc()

async def main() -> None:
    """游戏主循环，包含重玩逻辑"""
    while True:
        try:
            await setup_and_run_game()
        except Exception as e:
            print(f"\n游戏设置或运行期间发生严重错误: {e}")
            import traceback
            traceback.print_exc()

        play_again = input("\n是否开始新的一局？ (y/n): ")
        if play_again.lower().strip() != 'y':
            print("感谢游玩，再见！")
            break

if __name__ == "__main__":
    asyncio.run(main())
