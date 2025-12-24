"""
测试思考标签过滤功能
"""
import re

def remove_thinking_tags(text: str) -> str:
    """
    移除文本中的 <think>...</think> 标签及其内容。
    """
    # 使用正则表达式移除 <think>...</think> 标签（包括标签内的所有内容）
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 也处理可能的变体
    cleaned_text = re.sub(r'</?think(?:ing)?>.*?</think(?:ing)?>', '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
    
    # 清理多余的空行
    cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
    
    return cleaned_text.strip()

# 测试用例
test_text1 = """<think>我需要分析当前的情况...</think>作为Player_6，我同意大家的观点。"""

test_text2 = """首先，我需要分析当前的发言情况。
<think>
从发言记录来看：
- Player_0：发言简短
- Player_1：建议预言家透露信息
我决定怀疑Player_0
</think>
作为Player_6，我同意大家的观点，平安夜说明女巫使用了解药。"""

test_text3 = """</think>作为Player_6，我同意大家的观点"""

print("=" * 60)
print("测试1 - 单行思考标签")
print("=" * 60)
print("原文:")
print(test_text1)
print("\n过滤后:")
print(remove_thinking_tags(test_text1))

print("\n" + "=" * 60)
print("测试2 - 多行思考标签")
print("=" * 60)
print("原文:")
print(test_text2)
print("\n过滤后:")
print(remove_thinking_tags(test_text2))

print("\n" + "=" * 60)
print("测试3 - 只有结束标签")
print("=" * 60)
print("原文:")
print(test_text3)
print("\n过滤后:")
print(remove_thinking_tags(test_text3))

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
