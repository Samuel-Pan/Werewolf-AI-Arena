# werewolf_game/agents/player_agent.py

import os
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIMultiAgentFormatter

# 定义prompts文件夹的路径
PROMPT_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')

def create_player_agent(
    role: str,
    model_config: dict,
    agent_id: int = None,
) -> ReActAgent:
    """
    一个用于创建玩家Agent的工厂函数

    Args:
        role (str): 玩家的角色 (e.g., "werewolf", "seer").
        model_config (dict): 包含模型API所需配置的字典.
            例如:
            {
                "model": "deepseek-ai/DeepSeek-V3.2-Exp",
                "api_key": "YOUR_API_KEY",
                "base_url": "YOUR_BASE_URL"
            }
        agent_id (int, optional): agent的唯一id. Defaults to None.

    Returns:
        ReActAgent: 根据配置实例化的Agent.
    """
    # 1. 读取对应角色的系统提示
    prompt_path = os.path.join(PROMPT_DIR, f"{role}.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found for role: {role}")
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt = f.read()

    # 2. 初始化模型
    # AgentScope的OpenAIChat可以兼容所有OpenAI API标准的接口
    model_init_args = {
        "model_name": model_config["model_name"],
        "api_key": model_config["api_key"],
    }
    # 检查是否有base_url，并将其放入client_args
    if "base_url" in model_config and model_config["base_url"]:
        model_init_args["client_args"] = {
            "base_url": model_config["base_url"]
        }
    
    # 增加网络请求重试机制
    # model_init_args["max_retries"] = 5
    
    # 【修复】通过 generate_kwargs 禁用工具调用，避免 "tool_calls" 错误
    model_init_args["generate_kwargs"] = {
        "tool_choice": "none"
    }
    
    model = OpenAIChatModel(**model_init_args)

    # 3. 创建并返回Agent实例
    # 我们使用基础的Agent，因为它更适合纯对话驱动的决策
    agent_name = f"{role.capitalize()}_{agent_id}" if agent_id is not None else role.capitalize()

    agent = ReActAgent(
        name=agent_name,
        sys_prompt=prompt,
        model=model,
        formatter=OpenAIMultiAgentFormatter(),
        max_iters=1,
    )
    
    # 为AI agent添加一个is_user属性，以便裁判进行区分
    setattr(agent, 'is_user', False)
    
    return agent
