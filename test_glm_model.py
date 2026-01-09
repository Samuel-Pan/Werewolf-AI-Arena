# import asyncio
# from agentscope.agent import ReActAgent
# from agentscope.message import Msg
# from agentscope.model import OpenAIChatModel
# from agentscope.formatter import OpenAIMultiAgentFormatter
# import io
# import contextlib

# # 创建一个临时的输出缓冲区
# f = io.StringIO()

# from configs import MODELSCOPE_API_KEY, MODEL_BASE_URL, MODEL_LIST

# async def test_qwen_model():
#     """
#     一个简单的测试函数，用于验证 Qwen 模型是否能正常工作。
#     """
#     print("===== 开始测试 Qwen 模型... =====")

#     # 1. 检查API Key是否已配置
#     if MODELSCOPE_API_KEY == "你的MODELSCOPE_TOKEN" or not MODELSCOPE_API_KEY:
#         print("错误：请先在 configs.py 文件中配置你的 MODELSCOPE_API_KEY！")
#         return

#     # 2. 配置 Qwen 模型
#     qwen_config = {
#         "model_name": MODEL_LIST["qwen"],
#         "api_key": MODELSCOPE_API_KEY,
#         "base_url": MODEL_BASE_URL,
#     }
    
#     model = OpenAIChatModel(
#         model_name=qwen_config["model_name"],
#         api_key=qwen_config["api_key"],
#         client_args={"base_url": qwen_config["base_url"]},
#     )

#     # 3. 创建一个ReactAgent实例
#     # ReActAgent需要一个system_prompt来定义其角色和能力
#     system_prompt = "你是一个乐于助人的AI助手。"
#     agent = ReActAgent(
#         name="Qwen_Tester",
#         model=model,
#         sys_prompt=system_prompt,
#         formatter=OpenAIMultiAgentFormatter(),
#     )

#     # 4. 定义要发送的消息
#     prompt = "你好，给我介绍一下AI就好"
#     message = Msg(name="user", content=prompt, role="user")

#     print(f"\n发送给模型的提示词: '{prompt}'")
#     print("正在等待模型回复...")

#     # 5. 获取并打印回复
#     try:
#         with contextlib.redirect_stdout(f):
#             response = await agent.reply(message)
#         print("\n===== 模型回复 =====")
#         print(response.content)
#         print("======================")
#     except Exception as e:
#         print(f"\n测试过程中出现错误: {e}")
#         import traceback
#         traceback.print_exc()

# if __name__ == "__main__":
#     asyncio.run(test_qwen_model())


raw_response = "我开枪带走: Player_8"
parsed_candidate = raw_response.strip() if raw_response else ""
# 处理可能的 JSON 字符串或转义
try:
    import json
    # 如果是被额外引号包裹的 JSON 字符串，先去掉外部引号并解码转义
    if parsed_candidate.startswith('"') and parsed_candidate.endswith('"'):
        inner = parsed_candidate[1:-1]
        try:
            parsed_candidate = inner.encode('utf-8').decode('unicode_escape')
        except Exception:
            parsed_candidate = inner
    # 尝试解析 JSON，提取可能的字段
    if parsed_candidate.startswith('{') or '"response"' in parsed_candidate:
        parsed_json = json.loads(parsed_candidate)
        if isinstance(parsed_json, dict):
            # 优先使用常见字段
            parsed_candidate = parsed_json.get('response') or parsed_json.get('content') or next(iter(parsed_json.values()), parsed_candidate)
except Exception:
    # 解析失败则继续使用原始文本
    pass

# 如果包含格式化指令，提取冒号后的部分
if '我开枪带走:' in parsed_candidate or '我开枪带走：' in parsed_candidate:
    parsed_candidate = parsed_candidate.split(':')[-1].split('：')[-1].strip()

print(f"最终解析结果: '{parsed_candidate}'")

for p_target in ["player_1", "player2", "Player_3", "player 4", "5", "Player_8"]:
    player_id = p_target.split('_')[-1]
    normalized_input = parsed_candidate.lower().strip()
    print(normalized_input)
    # 【调试】记录匹配过程
    # game_logger.add_entry(f"[猎人开枪匹配]: 尝试匹配 '{normalized_input}' 与 '{p_target}' (ID={player_id})")

    # 支持的格式：Player_6, player_6, player6, player 6, 6
    if normalized_input == p_target.lower() or \
        normalized_input == f"player_{player_id}" or \
        normalized_input == f"player{player_id}" or \
        normalized_input == f"player {player_id}" or \
        normalized_input == f"player-{player_id}" or \
        normalized_input == player_id or \
        p_target.lower() in normalized_input:
        target_name = p_target
        # game_logger.add_entry(f"[猎人开枪匹配成功]: '{normalized_input}' 匹配到 '{p_target}'")
        print(target_name)
        break