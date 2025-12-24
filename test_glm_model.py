import asyncio
from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIMultiAgentFormatter
import io
import contextlib

# 创建一个临时的输出缓冲区
f = io.StringIO()

from configs import MODELSCOPE_API_KEY, MODEL_BASE_URL, MODEL_LIST

async def test_qwen_model():
    """
    一个简单的测试函数，用于验证 Qwen 模型是否能正常工作。
    """
    print("===== 开始测试 Qwen 模型... =====")

    # 1. 检查API Key是否已配置
    if MODELSCOPE_API_KEY == "你的MODELSCOPE_TOKEN" or not MODELSCOPE_API_KEY:
        print("错误：请先在 configs.py 文件中配置你的 MODELSCOPE_API_KEY！")
        return

    # 2. 配置 Qwen 模型
    qwen_config = {
        "model_name": MODEL_LIST["qwen"],
        "api_key": MODELSCOPE_API_KEY,
        "base_url": MODEL_BASE_URL,
    }
    
    model = OpenAIChatModel(
        model_name=qwen_config["model_name"],
        api_key=qwen_config["api_key"],
        client_args={"base_url": qwen_config["base_url"]},
    )

    # 3. 创建一个ReactAgent实例
    # ReActAgent需要一个system_prompt来定义其角色和能力
    system_prompt = "你是一个乐于助人的AI助手。"
    agent = ReActAgent(
        name="Qwen_Tester",
        model=model,
        sys_prompt=system_prompt,
        formatter=OpenAIMultiAgentFormatter(),
    )

    # 4. 定义要发送的消息
    prompt = "你好，给我介绍一下AI就好"
    message = Msg(name="user", content=prompt, role="user")

    print(f"\n发送给模型的提示词: '{prompt}'")
    print("正在等待模型回复...")

    # 5. 获取并打印回复
    try:
        with contextlib.redirect_stdout(f):
            response = await agent.reply(message)
        print("\n===== 模型回复 =====")
        print(response.content)
        print("======================")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_qwen_model())
