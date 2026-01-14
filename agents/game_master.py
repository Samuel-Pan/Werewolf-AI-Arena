# werewolf_game/agents/game_master.py

import asyncio
import sys
import os
import io
import contextlib
from typing import List, Dict, Union, Optional, Tuple
from agentscope.agent import AgentBase, UserAgent, ReActAgent
# from agentscope.model import ModelWrapperBase
from agentscope.message import Msg
from agentscope.pipeline import MsgHub
from collections import Counter
import random
import re
from logger import game_logger, prompt_logger, memory_logger # 【新功能】引入prompt_logger和memory_logger
from agentscope.formatter import OpenAIMultiAgentFormatter

# 角色中英文映射
ROLE_CN_MAP = {
    "werewolf": "狼人",
    "seer": "预言家",
    "witch": "女巫",
    "hunter": "猎人",
    "villager": "村民"
}


class GameMasterAgent(ReActAgent):
    """
    狼人杀游戏的裁判Agent。
    负责维护游戏状态、推进游戏流程、并做出裁决。
    """
    def __init__(
        self,
        # players: List[AgentBase],
        players: List[ReActAgent],
        player_identities: Dict[str, str],
        model: None,
        summary_model: None,  # 新增：专门用于生成摘要的模型
    ) -> None:
        """
        初始化裁判Agent。

        Args:
            players (List[ReActAgent]): 参与游戏的所有玩家Agent的列表.
            player_identities (Dict[str, str]): 一个字典，key是玩家名，value是角色身份.
            model (ModelWrapperBase, optional): 为裁判配置的语言模型（主模型）. Defaults to None.
            summary_model (ModelWrapperBase, optional): 专门用于生成记忆摘要的模型. Defaults to None.
        """
        # 【重要更新】将name硬编码，并接收model参数
        # super().__init__()
        # self.name = "Game_Master"
        # self.model = model
        super().__init__(
            name="Game_Master",
            sys_prompt="你是狼人杀游戏的裁判，负责生成游戏摘要。",
            model=model,
            max_iters=1,
            formatter=OpenAIMultiAgentFormatter(),
        )
        
        # 保存专门用于生成摘要的模型，如果没有提供则使用主模型
        self.summary_model = summary_model if summary_model is not None else model
        
        # 初始化游戏状态机
        self.game_state = {
            "players": {p.name: {"agent": p, "status": "alive", "memory_summary": ""} for p in players},
            "identities": player_identities,
            "day": 0,
            "phase": "INIT", # 游戏阶段: INIT, NIGHT, DAY_DISCUSSION, VOTE, END
            "game_over": False,
            "winner": None,
            "night_info": {
                "killed_by_werewolf": None,
                "poisoned": None,
                "saved": False,
                "death_cause": {},  # 记录每个死亡玩家的死因 {player_name: "werewolf"/"poison"/"vote"}
            },  # 存放夜晚发生事件的记录
            # 【新功能】记录女巫药的使用情况
            "witch_potions": {"save": True, "poison": True},
            "discussion_history": [],
            "full_history": [], # 【新功能】长期记忆模块
        }

        # 构造游戏配置的系统提示信息
        num_players = len(players)
        # 将角色转换为中文并统计
        roles_summary = ", ".join(
            f"{count} {ROLE_CN_MAP.get(role, role)}" 
            for role, count in Counter(player_identities.values()).items()
        )
        self.game_initial_info = (
            f"本局游戏共有 {num_players} 名玩家，角色配置为：{roles_summary}。"
        )

        game_logger.start_game(self.game_state["identities"])
        prompt_logger.start_logging() # 【新功能】为新游戏初始化prompt日志
        self._setup_msghub(players)

        print("===== 游戏开始，裁判已就位 =====")

        # print("玩家列表:")
        # for name, role in self.game_state["identities"].items():
        #     print(f"- {name}: {role}")
        # print("===============================")


    def _setup_msghub(self, players: List[AgentBase]) -> None:
        """创建并配置公共和私密通信频道"""
        # 提取狼人
        werewolves = [
            p for p in players if self.game_state["identities"][p.name] == "werewolf"
        ]
        
        # 创建一个专用于狼人的私密频道
        self.werewolf_channel = MsgHub(participants=werewolves)
        print("已创建狼人私密通信频道。")
        
        # 创建一个所有玩家共享的公共频道
        self.public_channel = MsgHub(participants=players)
        print("已创建游戏公共通信频道。")

    async def notify_werewolves_of_teammates(self) -> None:
        """向所有狼人玩家（包括AI和人类）私密地通知他们的队友。"""
        werewolf_names = [
            p_name
            for p_name, p_role in self.game_state["identities"].items()
            if p_role == "werewolf"
        ]

        for werewolf_name in werewolf_names:
            teammates = [name for name in werewolf_names if name != werewolf_name]
            
            if teammates:
                teammate_str = ", ".join(teammates)
                notification = f"你是狼人，你的队友是: {teammate_str}。"
            else:
                notification = "你是场上唯一的狼人。"

            # 获取玩家agent实例
            player_agent = self.game_state["players"][werewolf_name]["agent"]

            # 根据agent类型（用户或AI）发送不同的私密消息
            if getattr(player_agent, 'is_user', False):
                # UserAgent 会特殊处理带 __PRIVATE__ 前缀的消息
                await player_agent.observe(Msg(self.name, f"__PRIVATE__{notification}", role="system"))
            else:
                # 对于AI Agent，直接发送一个私密的系统观察消息
                await player_agent.observe(Msg(self.name, notification, role="system"))


    async def run_game(self) -> None:
        """
        游戏的主循环。
        """
        # 【新功能】在游戏开始时广播一次游戏设置
        await self._announce_game_setup()

        while not self.game_state["game_over"]:
            # 1. 增加天数
            self.game_state["day"] += 1
            print(f"\n\n===== 第 {self.game_state['day']} 天 =====")

            # 重置夜晚信息
            self.game_state["night_info"] = {
                "killed_by_werewolf": None,
                "poisoned": None,
                "saved": False,
                "death_cause": {},
            }

            # 2. 进入夜晚阶段
            await self._night_phase()
            if self.game_state["game_over"]: break

            # 3. 进入白天阶段
            await self._day_phase()
            if self.game_state["game_over"]: break
            
            # 4. 进入投票阶段
            await self._vote_phase()
            if self.game_state["game_over"]: break

        winner = self.game_state['winner']
        identities = self.game_state["identities"]
        
        print(f"\n===== 游戏结束！胜利者是: {winner} =====")
        game_logger.add_entry(f"\n===== 游戏结束！胜利者是: {winner} =====")
        
        # 在控制台打印身份信息
        print("\n===== 游戏结束 - 最终身份揭晓 =====")
        for name, role in identities.items():
            print(f"- {name}: {role}")
        print("====================================")

        # 在日志中记录身份信息
        game_logger.log_identities_at_end(identities)
        game_logger.save_log() # 保存日志


    async def _night_phase(self) -> None:
        """
        处理夜晚阶段的逻辑。
        """
        self.game_state["phase"] = "NIGHT"
        log_entry = f"\n--- 第 {self.game_state['day']} 天 - 夜晚 ---"
        game_logger.add_entry(log_entry)
        await self._announce_to_public("天黑请闭眼...", role="system", to_print=True)
        
        # 记忆已经在投票阶段结束后更新了，这里不需要再更新
        
        # 1. 狼人行动
        await self._werewolf_action()
        
        # 2. 预言家行动
        if self._get_alive_players_by_role("seer"):
            await self._seer_action()

        # 3. 女巫行动
        if self._get_alive_players_by_role("witch"):
            await self._witch_action()

    async def _get_silent_reply(self, agent: AgentBase, prompt: str) -> Msg:
        """
        一个辅助函数，用于从AI Agent处获取回复而不打印到控制台。
        通过临时重定向标准输出和标准错误来实现静默。
        支持429限流错误时自动切换模型重试。
        """
        # 检查是否为用户代理，如果是，则直接调用其 reply 方法
        # 这样可以避免捕获和打印用户代理的输入提示
        if isinstance(agent, UserAgent):
            return await agent.reply(Msg(self.name, prompt, role="user"))

        # 对于AI代理，使用静默方式获取回复
        max_retries = 3  # 最多重试3次（包括切换模型）
        for retry_count in range(max_retries):
            f = io.StringIO()
            with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                try:
                    response_msg = await agent.reply(Msg(self.name, prompt, role="user"))
                    # 成功则直接返回
                    break
                except Exception as e:
                    error_str = str(e)
                    is_rate_limit = "429" in error_str or "rate limit" in error_str.lower()
                    
                    # 【增强日志】当捕获到异常时，记录更详细的信息（但不记录prompt）
                    game_logger.add_entry(f"[{agent.name} answer error (尝试 {retry_count + 1}/{max_retries})]:\n"
                                          f"  - Error: {e}\n"
                                          f"  - Raw Exception Details: {e.args}")
                    
                    # 如果是429限流错误且还有重试机会，尝试切换模型
                    if is_rate_limit and retry_count < max_retries - 1:
                        game_logger.add_entry(f"[检测到429限流，尝试为 {agent.name} 切换模型]")
                        success = await self._switch_agent_model(agent)
                        if success:
                            game_logger.add_entry(f"[{agent.name} 模型切换成功，准备重试]")
                            continue  # 继续下一次循环重试
                        else:
                            game_logger.add_entry(f"[{agent.name} 模型切换失败，使用原模型继续]")
                    
                    # 当 ReActAgent 解析失败时，异常 e 可能包含原始的模型输出
                    # 我们尝试从中提取纯文本内容，以保证游戏流程继续
                    raw_response = ""
                    # 检查 e.args 中是否包含类似Msg的结构
                    if e.args:
                        first_arg = e.args[0]
                        if isinstance(first_arg, dict) and 'content' in first_arg:
                            raw_response = first_arg['content']
                        elif isinstance(first_arg, list) and first_arg:
                            # 尝试从列表的第一个元素中提取
                            if isinstance(first_arg[0], dict) and 'content' in first_arg[0]:
                                raw_response = first_arg[0]['content']
                    
                    if not raw_response:
                        if "'response':" in error_str:
                            try:
                                import json
                                dict_str = error_str[error_str.find("{") : error_str.rfind("}") + 1]
                                json_str = dict_str.replace("'", "\"")
                                error_dict = json.loads(json_str)
                                if 'response' in error_dict:
                                    raw_response = error_dict['response']
                            except Exception:
                                pass # 解析失败则忽略
                    
                    response_msg = Msg(agent.name, str(raw_response), role="assistant")
                    break  # 已处理异常，退出重试循环

        captured_output = f.getvalue()
        if "thinking" in captured_output or "<think>" in captured_output.lower():
             game_logger.add_entry(f"[{agent.name} thinking process]: {captured_output.strip()}")
        
        # 【新增】检查response内容中是否包含思考标签，如果有则记录到日志
        if hasattr(response_msg, 'content'):
            content_str = str(response_msg.content)
            if "<think>" in content_str.lower():
                # 提取思考内容
                import re
                think_match = re.search(r'<think>(.*?)</think>', content_str, re.DOTALL | re.IGNORECASE)
                if think_match:
                    thinking_content = think_match.group(1).strip()
                    game_logger.add_entry(f"[{agent.name} <think> content]: {thinking_content}")
            
        return response_msg

    async def _switch_agent_model(self, agent: AgentBase) -> bool:
        """
        当检测到429限流错误时，为agent切换到其他可用模型。
        
        Returns:
            bool: 切换成功返回True，否则返回False
        """
        try:
            # 导入配置
            from configs import MODEL_LIST, API_PROVIDERS
            from agentscope.model import OpenAIChatModel
            
            # 获取当前模型名称
            current_model_name = getattr(agent.model, 'model_name', None)
            if not current_model_name:
                return False
            
            # 找出当前使用的是哪个模型key
            current_model_key = None
            for key, model_id in MODEL_LIST.items():
                if model_id == current_model_name:
                    current_model_key = key
                    break
            
            # 获取所有可用的其他模型
            available_models = [key for key in MODEL_LIST.keys() if key != current_model_key]
            
            if not available_models:
                game_logger.add_entry(f"[{agent.name}] 没有其他可用模型")
                return False
            
            # 随机选择一个新模型
            import random
            new_model_key = random.choice(available_models)
            new_model_id = MODEL_LIST[new_model_key]
            
            # 获取API配置（假设都使用modelscope）
            provider_config = API_PROVIDERS["modelscope"]
            
            # 创建新模型实例
            model_init_args = {
                "model_name": new_model_id,
                "api_key": provider_config["api_key"],
            }
            
            if "base_url" in provider_config and provider_config["base_url"]:
                model_init_args["client_args"] = {
                    "base_url": provider_config["base_url"]
                }
            
            # 禁用工具调用
            model_init_args["generate_kwargs"] = {
                "tool_choice": "none"
            }
            
            new_model = OpenAIChatModel(**model_init_args)
            
            # 替换agent的模型
            agent.model = new_model
            
            game_logger.add_entry(f"[{agent.name}] 成功切换模型: {current_model_key}({current_model_name}) -> {new_model_key}({new_model_id})")
            return True
            
        except Exception as e:
            game_logger.add_entry(f"[{agent.name}] 切换模型时发生错误: {e}")
            return False
    
    def _get_agent_model_info(self, agent) -> str:
        """
        获取Agent当前使用的模型信息
        返回格式: "model_key(model_id)" 或 "Unknown"
        """
        try:
            # 对于人类用户，返回特殊标记
            if getattr(agent, 'is_user', False):
                return "Human"
            
            # 获取模型名称
            current_model_name = getattr(agent.model, 'model_name', None)
            if not current_model_name:
                return "Unknown"
            
            # 导入配置（避免循环导入）
            from configs import MODEL_LIST
            
            # 查找对应的模型key
            for key, model_id in MODEL_LIST.items():
                if model_id == current_model_name:
                    return f"{key}({model_id})"
            
            # 如果没找到对应的key，直接返回model_name
            return f"Unknown({current_model_name})"
            
        except Exception:
            return "Unknown"

    def _parse_ai_response(self, content: any) -> str:
        """
        一个健壮的解析函数，用于从AI的回复内容中提取纯文本。
        它可以递归地处理字典、列表和纯字符串等多种格式。
        同时会过滤掉 <think> 标签中的思考过程。
        """
        # 1. 如果是字典（ReActAgent的标准输出）
        if isinstance(content, dict):
            if "speak" in content:
                text = str(content["speak"]).strip()
            elif "content" in content:
                text = str(content["content"]).strip()
            else:
                text = str(content)
        # 2. 如果是列表
        elif isinstance(content, list) and content:
            # 递归地解析列表的第一个元素
            text = self._parse_ai_response(content[0])
        # 3. 如果是纯字符串
        elif isinstance(content, str):
            text = content.strip()
        # 4. 其他情况或空内容
        else:
            text = str(content) if content is not None else ""
        
        # 【新增】过滤掉 <think> 标签内的思考过程
        text = self._remove_thinking_tags(text)
        
        return text
    
    def _remove_thinking_tags(self, text: str) -> str:
        """
        移除文本中的 <think>...</think> 标签及其内容。
        支持多行和嵌套的情况。
        """
        import re
        # 使用正则表达式移除 <think>...</think> 标签（包括标签内的所有内容）
        # re.DOTALL 使 . 匹配包括换行符在内的所有字符
        # 非贪婪匹配 .*? 确保只匹配最近的闭合标签
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 也处理可能的变体，如 </think> 或 <thinking>
        cleaned_text = re.sub(r'</?think(?:ing)?>.*?</think(?:ing)?>', '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
        
        # 清理多余的空行
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
        
        return cleaned_text.strip()

    async def _werewolf_action(self) -> None:
        """处理狼人讨论和刀人的逻辑（包含2轮讨论 + 最终决策）"""
        await self._announce_to_public("狼人请睁眼，商量要淘汰的玩家。", role="system", to_print=True)
        
        alive_werewolves_data = self._get_alive_players_by_role("werewolf")
        if not alive_werewolves_data:
            return

        alive_werewolves_agents = [data["agent"] for data in alive_werewolves_data]
        coordinator_wolf = alive_werewolves_agents[0]  # 指定第一个狼人作为最终决策者

        potential_targets = [
            p_name for p_name, p_info in self.game_state["players"].items()
            if p_info["status"] == "alive" and self.game_state["identities"][p_name] != "werewolf"
        ]
        if not potential_targets:
            return

        # 【新增】狼人讨论阶段（2轮）
        discussion_history = await self._werewolf_discussion(alive_werewolves_agents, potential_targets)

        # 最终决策阶段：由协调者综合讨论做出决定
        memory_summary = self._get_player_memory(coordinator_wolf.name)
        
        # 3. 构建狼人队友信息
        werewolf_teammates = [p_name for p_name, p_role in self.game_state["identities"].items() 
                             if p_role == "werewolf" and p_name != coordinator_wolf.name]
        teammates_status = []
        for name in werewolf_teammates:
            status = self.game_state["players"][name]["status"]
            teammates_status.append(f"{name}({status})")
        
        teammates_info = ""
        if werewolf_teammates:
            teammates_info = f"你的狼人队友状态: {', '.join(teammates_status)}。"
        else:
            teammates_info = "你是场上唯一的狼人。"

        # 4. 直接向协调者提问，并等待其回复，同时注入上下文
        target_name = None
        
        # 构建讨论内容展示（如果进行了讨论）
        discussion_summary = ""
        if discussion_history:
            discussion_content = "\n".join(discussion_history)
            discussion_summary = (
                f"\n=== 刚才的讨论记录 ===\n"
                f"{discussion_content}\n"
            )
        
        prompt_to_coordinator = (
            f"你是 {coordinator_wolf.name}，你的身份是【{ROLE_CN_MAP['werewolf']}】。现在是第 {self.game_state['day']} 天的夜晚。\n\n"
            f"=== 你的狼人队友信息 ===\n{teammates_info}\n\n"
            f"=== 游戏至今的记忆摘要 ===\n{memory_summary}"
            f"{discussion_summary}\n"
            f"=== 你的任务 ===\n"
            f"请从以下玩家中选择一个淘汰：\n{', '.join(potential_targets)}\n"
            f"综合考虑之前的游戏进程、当前局势{'和刚才的讨论内容' if discussion_history else ''}，选择对狼人阵营最有利的目标。\n"
            f"请先进行思考，然后严格以'我们决定淘汰: [玩家姓名]'的格式给出你的最终答案。"
        )
        if isinstance(coordinator_wolf, UserAgent):
                prompt_to_coordinator = (f"你是狼人团队的代表。请从以下玩家中选择一个淘汰：\n{', '.join(potential_targets)}\n请输入你要淘汰的玩家姓名或编号：")

        for _ in range(3): # 最多尝试3次
            # 【新功能】记录Prompt
            prompt_logger.add_prompt(
                title=f"向 {coordinator_wolf} (狼人代表) 提问淘汰目标",
                prompt=prompt_to_coordinator
            )
            # 使用静默回复来避免泄露信息
            response_msg = await self._get_silent_reply(coordinator_wolf, prompt_to_coordinator)
            # 【修复】使用新的健壮解析函数
            raw_response = self._parse_ai_response(response_msg.content)
            
            # 【新增】获取模型信息并记录到日志
            model_info = self._get_agent_model_info(coordinator_wolf)
            game_logger.add_entry(f"[{coordinator_wolf.name} 狼人击杀回复 - {model_info}]: {raw_response}")

            # 统一处理来自用户和AI的输入
            parsed_name = raw_response
            if "我们决定淘汰:" in raw_response:
                parsed_name = raw_response.split(":")[-1].strip()

            # 模糊匹配
            for p_target in potential_targets:
                player_id = p_target.split('_')[-1]
                if parsed_name.lower() == p_target.lower() or \
                    parsed_name.lower() == f"player{player_id}" or \
                    parsed_name.lower() == f"player {player_id}" or \
                    parsed_name.lower() == player_id or \
                    parsed_name in p_target:
                    target_name = p_target
                    break
            
            if target_name:
                break
            else:
                # 对用户和AI都进行提示
                error_msg = "无效的输入或目标。请严格按照格式，并从列表中选择一名玩家。"
                await coordinator_wolf.observe(Msg(self.name, error_msg, role="system"))
                if isinstance(coordinator_wolf, UserAgent):
                    print(error_msg) # 确保用户能看到
        
        # 3. 处理结果
        if target_name:
            self.game_state["night_info"]["killed_by_werewolf"] = target_name
            log_entry = f"狼人团队决定淘汰: {target_name}"
            
            # 【修复】狼人击杀是私密信息，只记录到 game_logger，不记录到 full_history
            # full_history 中只记录公开的裁判公告（在白天开始时记录）
            game_logger.add_entry(log_entry)
            
            await self._announce_to_public("狼人已完成击杀。", role="system", to_print=False)
            # 将最终决定广播回狼人频道，让队友知晓
            await self.werewolf_channel.broadcast(Msg(self.name, f"已确认，本次淘汰目标: {target_name}", role="system"))
        else:
            # 如果AI多次无法给出有效回复，裁判随机选择
            fallback_target = random.choice(potential_targets)
            self.game_state["night_info"]["killed_by_werewolf"] = fallback_target
            log_entry = f"狼人代表未能提供有效目标，裁判随机选择淘汰: {fallback_target}"
            
            # 【修复】将随机击杀记录也添加到 full_history
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-夜晚]: {log_entry}")
            game_logger.add_entry(log_entry)
            
            await self._announce_to_public("狼人已完成击杀。", role="system", to_print=False)

    async def _werewolf_discussion(self, werewolves: list, potential_targets: list) -> list:
        """
        狼人讨论阶段：2轮讨论，每个狼人依次发言
        使用 MsgHub 让狼人看到完整的讨论历史
        
        Returns:
            list: 讨论历史记录，格式为 ["Player_X: 发言内容", ...]
        """
        discussion_history = []  # 用于收集讨论内容
        
        if len(werewolves) == 1:
            # 只有一个狼人，无需讨论
            game_logger.add_entry("[狼人讨论]: 只有一个狼人存活，跳过讨论阶段")
            return discussion_history
        
        # 宣布讨论开始
        discussion_intro = (
            f"狼人团队讨论开始。当前存活的狼人有：{', '.join([w.name for w in werewolves])}\n"
            f"可选择的击杀目标：{', '.join(potential_targets)}\n"
            f"现在进行2轮讨论，每人依次发言，讨论击杀策略。"
        )
        await self.werewolf_channel.broadcast(Msg(self.name, discussion_intro, role="system"))
        game_logger.add_entry(f"[狼人讨论开始]: {len(werewolves)}名狼人，2轮讨论")
        
        # 进行2轮讨论
        for round_num in range(1, 3):
            round_intro = f"\n===== 第 {round_num} 轮讨论 ====="
            await self.werewolf_channel.broadcast(Msg(self.name, round_intro, role="system"))
            
            for werewolf in werewolves:
                # 获取狼人的记忆摘要
                memory_summary = self._get_player_memory(werewolf.name)
                
                # 构建队友信息
                teammates = [w.name for w in werewolves if w.name != werewolf.name]
                teammates_info = f"你的队友：{', '.join(teammates)}" if teammates else "你是唯一的狼人"
                
                # 根据轮次构建不同的提示词
                if round_num == 1:
                    task_instruction = (
                        f"请分析当前局势，提出你认为最佳的击杀目标，并说明理由。\n"
                        f"考虑因素：\n"
                        f"- 谁最可能是神职（预言家、女巫、猎人）\n"
                        f"- 谁对狼人威胁最大\n"
                        f"- 谁最有可能带领好人阵营\n"
                        f"简洁发言，1-2句话即可。"
                    )
                else:  # round_num == 2
                    task_instruction = (
                        f"这是第二轮讨论。请综合队友的意见，表达你的看法。\n"
                        f"可以同意队友的建议，也可以提出不同意见。\n"
                        f"简洁发言，1-2句话即可。"
                    )
                
                # 构建完整的 Prompt
                prompt = (
                    f"你是 {werewolf.name}，你的身份是【{ROLE_CN_MAP['werewolf']}】。现在是第 {self.game_state['day']} 天夜晚的狼人讨论环节（第{round_num}/2轮）。\n\n"
                    f"=== 你的队友信息 ===\n{teammates_info}\n\n"
                    f"=== 游戏至今的记忆摘要 ===\n{memory_summary}\n\n" if self.game_state['day'] > 1 else "现在是游戏的第一晚，暂时还没有玩家发言，你们可以随机选择一个目标\n"
                    f"=== 可击杀目标 ===\n{', '.join(potential_targets)}\n\n"
                    f"=== 你的任务 ===\n{task_instruction}"
                )
                
                # 如果是人类玩家，简化提示
                if getattr(werewolf, 'is_user', False):
                    prompt = (
                        f"[狼人讨论 - 第{round_num}/2轮]\n"
                        f"队友：{', '.join(teammates)}\n"
                        f"可击杀：{', '.join(potential_targets)}\n"
                        f"请发言（1-2句话，提出或讨论击杀目标）："
                    )
                
                # 记录 Prompt
                prompt_logger.add_prompt(
                    title=f"狼人讨论 - {werewolf.name} (第{round_num}轮)",
                    prompt=prompt
                )
                
                # 使用静默回复避免在控制台显示（狼人讨论是私密的）
                response_msg = await self._get_silent_reply(werewolf, prompt)
                
                # 解析回复
                raw_response = self._parse_ai_response(response_msg.content)
                
                # 记录到日志（这是唯一应该记录的地方）
                model_info = self._get_agent_model_info(werewolf)
                game_logger.add_entry(f"[狼人讨论-第{round_num}轮-{werewolf.name}-{model_info}]: {raw_response}")
                
                # 收集讨论历史（用于后续传递给决策者）
                discussion_record = f"[第{round_num}轮] {werewolf.name}: {raw_response}"
                discussion_history.append(discussion_record)
                
                # 【新增】如果当前有人类狼人玩家，在控制台显示所有狼人的发言
                # 这样人类狼人可以看到队友的讨论
                if any(getattr(w, 'is_user', False) for w in werewolves):
                    print(f"{werewolf.name}: {raw_response}")
                
                # 广播到狼人频道（让其他狼人看到，但不在控制台显示）
                await self.werewolf_channel.broadcast(Msg(werewolf.name, raw_response, role="assistant"))
        
        # 讨论结束提示
        discussion_end = f"\n讨论结束。现在由 {werewolves[0].name} 作为代表，做出最终决策。"
        await self.werewolf_channel.broadcast(Msg(self.name, discussion_end, role="system"))
        game_logger.add_entry("[狼人讨论结束]: 进入最终决策阶段")
        
        return discussion_history  # 返回讨论历史

    async def _seer_action(self) -> None:
        """【新功能】实现预言家验人逻辑"""
        await self._announce_to_public("预言家请睁眼,选择你要查验的玩家。", role="system", to_print=True)
        seer_data = self._get_alive_players_by_role("seer")
        if not seer_data: return
        
        seer_agent = seer_data[0]["agent"]
        potential_targets = [p_name for p_name, p_info in self.game_state["players"].items() if p_info["status"] == "alive" and p_name != seer_agent.name]
        if not potential_targets: return
        
        # 1. 【优化】获取预言家的记忆摘要
        memory_summary = self._get_player_memory(seer_agent.name)
        
        # 2. 获取预言家的查验历史
        seer_history = [log for log in self.game_state["full_history"] if "查验了" in log and seer_agent.name in log]
        if seer_history:
            private_info = "你的查验历史如下：\n" + "\n".join(seer_history)
        else:
            private_info = "你还没有查验过任何人。"
        
        target_name = None
        prompt_to_seer = (
            f"你是 {seer_agent.name}，你的身份是【{ROLE_CN_MAP['seer']}】。现在是第 {self.game_state['day']} 天的夜晚。\n\n"
            f"=== 你的查验历史 ===\n{private_info}\n\n"
            f"=== 游戏至今的记忆摘要 ===\n{memory_summary}\n\n"
            f"=== 你的任务 ===\n"
            f"请从以下玩家中选择一位进行查验：\n{', '.join(potential_targets)}\n"
            f"综合考虑之前的游戏进程、你的查验历史和当前局势，选择一个你最想了解身份的玩家。\n"
            f"请以'我查验: [玩家姓名]'的格式回复。"
        )
        if getattr(seer_agent, 'is_user', False):
            prompt_to_seer = (f"你是预言家。请从以下玩家中选择一位进行查验：\n{', '.join(potential_targets)}\n请输入你要查验的玩家姓名或编号：")

        # 【新功能】记录Prompt
        prompt_logger.add_prompt(
            title=f"向 {seer_agent.name} (预言家) 提问查验目标",
            prompt=prompt_to_seer
        )
        # 使用静默回复来避免泄露信息
        response_msg = await self._get_silent_reply(seer_agent, prompt_to_seer)
        # 【修复】使用新的健壮解析函数
        raw_response = self._parse_ai_response(response_msg.content)

        # 【新增】获取模型信息并记录到日志
        model_info = self._get_agent_model_info(seer_agent)
        game_logger.add_entry(f"[{seer_agent.name} 预言家查验回复 - {model_info}]: {raw_response}")

        parsed_name = raw_response
        if "我查验:" in raw_response:
            parsed_name = raw_response.split(":")[-1].strip()

        for p_target in potential_targets:
            player_id = p_target.split('_')[-1]
            if parsed_name.lower() == p_target.lower() or \
                parsed_name.lower() == f"player{player_id}" or \
                parsed_name.lower() == f"player {player_id}" or \
                parsed_name.lower() == player_id or \
                parsed_name in p_target:
                target_name = p_target
                break
        
        if target_name:
            target_identity = self.game_state["identities"][target_name]
            result = "好人" if target_identity != "werewolf" else "狼人"
            log_entry = f"预言家 {seer_agent.name} 查验了 {target_name}，结果是【{result}】。"
            
            # 【修复】预言家查验是私密信息，只记录到 game_logger，不记录到 full_history
            game_logger.add_entry(log_entry)
            
            # 将查验结果私密地告诉预言家，使用特殊前缀标记
            await seer_agent.observe(Msg(self.name, f"__PRIVATE__查验结果：玩家 {target_name} 的身份是【{result}】。", role="system"))
            # 增加一个对外的模糊播报
            await self._announce_to_public("预言家已完成查验。", role="system", to_print=False)
        else:
            log_entry = f"预言家 {seer_agent.name} 未能提供有效查验目标。"
            
            # 【修复】将失败记录也添加到 full_history
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-夜晚]: {log_entry}")
            game_logger.add_entry(log_entry)
            
            # 使用特殊前缀标记私密消息
            await seer_agent.observe(Msg(self.name, "__PRIVATE__无效的查验目标。", role="system"))
            # 即使没有有效目标，也要有模糊播报以防暴露信息
            await self._announce_to_public("预言家已完成查验。", role="system", to_print=False)

    async def _witch_action(self) -> None:
        """【新功能】实现女巫用药逻辑"""
        await self._announce_to_public("女巫请睁眼。", role="system", to_print=True)
        witch_data = self._get_alive_players_by_role("witch")
        if not witch_data: return
        witch_agent = witch_data[0]["agent"]
        
        killed_player = self.game_state["night_info"].get("killed_by_werewolf", None)
        
        # 1. 【优化】获取女巫的记忆摘要
        memory_summary = self._get_player_memory(witch_agent.name)
        
        # 2. 获取女巫的药剂状态
        save_status = "可用" if self.game_state["witch_potions"]["save"] else "已用"
        poison_status = "可用" if self.game_state["witch_potions"]["poison"] else "已用"
        potion_info = f"你的药剂状态：解药[{save_status}]，毒药[{poison_status}]。"

        # 3. 处理解药
        if self.game_state["witch_potions"]["save"] and killed_player:
            prompt_save = ""
            # 【回调】恢复告知女巫被淘汰的玩家，并通过prompt引导其行为
            # 区分User和AI的提示
            if getattr(witch_agent, 'is_user', False):
                # 为人类用户提供明确的可接受输入集合和超时/默认行为说明
                prompt_save = (
                    f"今晚玩家 {killed_player} 被淘汰了。\n"
                    f"你是否要使用【解药】救他？\n"
                    f"请输入 'y' / 'yes' / '使用' / '是' 来使用解药；\n"
                    f"输入 'n' / 'no' / '不使用' / '跳过' 则不使用解药。\n"
                    f"（超过 30s 或输入其他内容将视为不使用解药）"
                )
            else:
                # AI Agent的提示，要求仅回复固定短语，便于解析
                await witch_agent.observe(Msg(self.name, f"__PRIVATE__今晚玩家 {killed_player} 被淘汰了。", role="system"))
                prompt_save = (
                    f"你是 {witch_agent.name}，你的身份是【{ROLE_CN_MAP['witch']}】。现在是第 {self.game_state['day']} 天的夜晚。\n\n"
                    f"=== 你的药剂信息 ===\n{potion_info}\n\n"
                    f"=== 游戏至今的记忆摘要 ===\n{memory_summary}\n\n"
                    f"=== 当前情况 ===\n"
                    f"今晚玩家 {killed_player} 被淘汰了。你有一瓶解药可以救他。\n"
                    f"综合考虑之前的游戏进程和当前局势，决定是否使用解药。\n\n"
                    f"如果你决定使用解药，请仅回复：使用解药\n"
                    f"如果你决定不使用解药，请仅回复：不使用解药"
                )
            
            # 【新功能】记录Prompt
            prompt_logger.add_prompt(
                title=f"向 {witch_agent.name} (女巫) 提问是否使用解药",
                prompt=prompt_save
            )
            # 使用静默回复来避免AI的决策过程被打印
            response_msg = await self._get_silent_reply(witch_agent, prompt_save)
            # 【修复】使用新的健壮解析函数
            raw_response = self._parse_ai_response(response_msg.content)

            # 【新增】获取模型信息并记录到日志
            model_info = self._get_agent_model_info(witch_agent)
            game_logger.add_entry(f"[{witch_agent.name} 女巫解药回复 - {model_info}]: {raw_response}")
            
            # 标准化并解析多种同义输入，默认兜底为不使用
            normalized = raw_response.strip().lower() if raw_response else ""
            affirmatives = ['y', 'yes', '使用', '是', '使用解药']
            negatives = ['n', 'no', '不使用', '跳过', '不使用解药']
            user_wants_to_save = False
            if getattr(witch_agent, 'is_user', False):
                if normalized in affirmatives:
                    user_wants_to_save = True
                else:
                    user_wants_to_save = False
            else:
                # 对于AI，优先检测明确短语 '使用解药'
                if '使用解药' in raw_response:
                    user_wants_to_save = True
                else:
                    user_wants_to_save = False

            if user_wants_to_save:
                self.game_state["night_info"]["saved"] = True
                self.game_state["witch_potions"]["save"] = False
                log_entry = f"女巫使用了【解药】救了 {killed_player}。"
                game_logger.add_entry(log_entry)
        
        # 2. 处理毒药 (同一晚不能同时用解药和毒药)
        if not self.game_state["night_info"]["saved"] and self.game_state["witch_potions"]["poison"]:
            potential_targets = [p_name for p_name, p_info in self.game_state["players"].items() if p_info["status"] == "alive" and p_name != witch_agent.name]
            if not potential_targets: 
                return
            
            prompt_poison = ""
            if getattr(witch_agent, 'is_user', False):
                info_msg = ""
                if not killed_player: # 只有在平安夜（没进入救人环节）时才需要主动告知
                    info_msg = "今晚是平安夜，没有人被淘汰。\n"
                prompt_poison = (f"{info_msg}你是否要使用【毒药】？\n"
                                 f"如果要使用，请输入你要毒杀的玩家姓名或编号。\n"
                                 f"如果不使用，直接按回车或输入 'n'/'no'。\n"
                                 f"可选目标: {', '.join(potential_targets)}")
            else:
                if not killed_player:
                    await witch_agent.observe(Msg(self.name, "__PRIVATE__今晚是平安夜，没有人被淘汰。", role="system"))
                prompt_poison = (
                    f"你是 {witch_agent.name}，你的身份是【{ROLE_CN_MAP['witch']}】。现在是第 {self.game_state['day']} 天的夜晚。\n\n"
                    f"=== 你的药剂信息 ===\n{potion_info}\n\n"
                    f"=== 游戏至今的记忆摘要 ===\n{memory_summary}\n\n"
                    f"=== 你的任务 ===\n"
                    f"你还有一瓶毒药，要对场上其他存活玩家使用吗？\n"
                    f"综合考虑之前的游戏进程和当前局势，决定是否使用毒药以及使用对象。\n"
                    f"如果要使用，请以'我毒杀: [玩家姓名]'的格式回复。\n"
                    f"如果不使用，请回复'不使用'。\n"
                    f"可选目标: {', '.join(potential_targets)}"
                )

            # 【新功能】记录Prompt
            prompt_logger.add_prompt(
                title=f"向 {witch_agent.name} (女巫) 提问是否使用毒药",
                prompt=prompt_poison
            )
            # 使用静默回复来避免AI的决策过程被打印
            response_msg = await self._get_silent_reply(witch_agent, prompt_poison)
            # 【修复】使用新的健壮解析函数
            raw_response = self._parse_ai_response(response_msg.content)

            # 【新增】获取模型信息并记录到日志
            model_info = self._get_agent_model_info(witch_agent)
            game_logger.add_entry(f"[{witch_agent.name} 女巫毒药回复 - {model_info}]: {raw_response}")

            target_name = None
            parsed_name = ""

            if getattr(witch_agent, 'is_user', False):
                if raw_response and raw_response.lower() not in ['n', 'no', '不使用']:
                    parsed_name = raw_response
            else:
                # AI 回复解析：支持多种格式
                if "我毒杀:" in raw_response or "我毒杀：" in raw_response:
                    parsed_name = raw_response.split(":")[-1].split("：")[-1].strip()
                elif "不使用" in raw_response or "跳过" in raw_response:
                    parsed_name = ""  # 明确不使用毒药
                else:
                    # 尝试从回复中提取玩家名称
                    parsed_name = raw_response.strip()

            if parsed_name:
                for p_target in potential_targets:
                    player_id = p_target.split('_')[-1]
                    if parsed_name.lower() == p_target.lower() or \
                       parsed_name.lower() == f"player{player_id}" or \
                       parsed_name.lower() == f"player {player_id}" or \
                       parsed_name.lower() == player_id or \
                       parsed_name in p_target:
                        target_name = p_target
                        break
            
            if target_name:
                self.game_state["night_info"]["poisoned"] = target_name
                self.game_state["witch_potions"]["poison"] = False
                log_entry = f"女巫使用了【毒药】，目标是 {target_name}。"
                game_logger.add_entry(log_entry)

    async def _night_settlement(self) -> List[Dict]:
        """【逻辑修正】夜晚结算只处理状态更新，不进行任何广播"""
        deaths = []
        killed_by_werewolf = self.game_state["night_info"].get("killed_by_werewolf")
        poisoned = self.game_state["night_info"].get("poisoned")
        saved = self.game_state["night_info"].get("saved")

        if killed_by_werewolf and not saved:
            deaths.append(killed_by_werewolf)
            self.game_state["night_info"]["death_cause"][killed_by_werewolf] = "werewolf"
        
        if poisoned and poisoned not in deaths:
            deaths.append(poisoned)
            self.game_state["night_info"]["death_cause"][poisoned] = "poison"

        dead_players_data = []
        if deaths:
            for player_name in deaths:
                self.game_state["players"][player_name]["status"] = "dead"
                dead_players_data.append(self.game_state["players"][player_name])
        
        self._check_win_condition()
        return dead_players_data

    async def _day_phase(self) -> None:
        """【逻辑修正】实现真实的白天发言环节"""
        self.game_state["phase"] = "DAY_DISCUSSION"
        
        # 1. 夜晚结算，只更新内部状态
        dead_players_data = await self._night_settlement()
        if self.game_state["game_over"]:
            return

        # 2. 公布夜晚结果
        night_summary = self._get_night_summary()
        self.game_state["full_history"].append(f"[第{self.game_state['day']}天-夜晚]: {night_summary}")
        await self._announce_to_public(night_summary, role="system", to_print=True)

        # 3. 在公布死亡后，处理遗言
        if dead_players_data:
            # 【新增】遗言规则：首夜死亡有遗言，第二夜及之后的夜晚死亡无遗言
            if self.game_state["day"] == 1:
                # 首夜死亡，有遗言
                await self._handle_last_words(dead_players_data)
            else:
                # 第二夜及之后，夜晚死亡无遗言
                game_logger.add_entry(f"[遗言规则]: 第{self.game_state['day']}夜死亡的玩家无遗言权")
                await self._announce_to_public("根据游戏规则，第二夜及之后的夜晚死亡玩家无遗言。", role="system", to_print=True)
            
            # 遗言后可能产生胜负
            if self.game_state["game_over"]:
                return

        day_start_announcement = "天亮了，现在进入自由发言环节。"
        self.game_state["full_history"].append(f"[第{self.game_state['day']}天-白天]: {day_start_announcement}")
        await self._announce_to_public(day_start_announcement, role="system", to_print=True)
        
        self.game_state["discussion_history"] = [] # 清空上一轮的发言
        alive_players_data = self._get_alive_players_by_role()
        
        # 【修复】不再统一生成摘要，而是在每个玩家发言前单独生成，避免并发限流
        
        # 按照玩家编号顺序发言
        for player_data in sorted(alive_players_data, key=lambda p: p['agent'].name):
            agent = player_data["agent"]
            
            # 【修复】在白天发言前为该玩家生成记忆摘要
            # 包含：以往记忆 + 昨晚事件 + 今天之前的玩家发言
            memory_summary = await self._generate_memory_summary(
                agent.name, 
                for_morning=True, 
                current_discussion=self.game_state["discussion_history"]  # 传递当天之前的发言
            )
            game_logger.add_entry(f"[白天发言前-为 {agent.name} 生成的记忆摘要]: {memory_summary}")

            # 【Prompt优化】为AI构建更丰富的上下文
            current_day = self.game_state['day']
            player_role = self.game_state["identities"][agent.name]
            
            # 1. 构建私密信息部分
            private_info = "你是一个普通村民，没有特殊信息。"
            if player_role == "seer":
                # 预言家可以看到自己的查验历史
                seer_history = [log for log in self.game_state["full_history"] if "查验了" in log and agent.name in log]
                if seer_history:
                    private_info = "你的查验历史如下：\n" + "\n".join(seer_history)
                else:
                    private_info = "你还没有查验过任何人。"
            elif player_role == "witch":
                save_status = "可用" if self.game_state["witch_potions"]["save"] else "已用"
                poison_status = "可用" if self.game_state["witch_potions"]["poison"] else "已用"
                private_info = f"你的药剂状态：解药[{save_status}]，毒药[{poison_status}]。"
            elif player_role == "werewolf":
                werewolf_teammates = [p_name for p_name, p_role in self.game_state["identities"].items() if p_role == "werewolf" and p_name != agent.name]
                teammates_info = ""
                if werewolf_teammates:
                    teammates_info = f"你的狼人队友是: {', '.join(werewolf_teammates)}。\n"
                else:
                    teammates_info = "你的狼人队友已经死亡，你现在是唯一的狼人。\n"
                
                # 【新增】狼人击杀历史
                werewolf_history = [log for log in self.game_state["full_history"] if "狼人团队决定淘汰" in log or "狼人代表未能提供有效目标" in log]
                if werewolf_history:
                    kill_history = "你们的击杀历史如下：\n" + "\n".join(werewolf_history)
                else:
                    kill_history = "你们还没有执行任何击杀行动。"
                
                private_info = teammates_info + kill_history

            # 2. 构建完整的Prompt
            alive_players_str = ", ".join([p["agent"].name for p in alive_players_data])
            history_str = "\n".join(self.game_state["discussion_history"]) if self.game_state["discussion_history"] else "你是第一个发言。"
            
            # 构建发言顺序提示
            speaker_order = [p["agent"].name for p in sorted(alive_players_data, key=lambda p: p['agent'].name)]
            current_index = speaker_order.index(agent.name)
            order_info = f"发言顺序：{' → '.join(speaker_order)}（你是第 {current_index + 1} 个发言）"
            
            prompt = (f"现在是第 {current_day} 天的白天发言环节。\n"
                      f"你是 {agent.name}，你的身份是【{ROLE_CN_MAP.get(player_role, player_role)}】。\n"
                      f"{order_info}\n\n"
                      f"=== 你的私密信息 ===\n{private_info}\n\n"
                      f"=== 你的专属记忆摘要 ===\n{memory_summary}\n\n"
                      f"=== 本轮公开信息 ===\n"
                      f"- 昨晚的公开信息是：{night_summary}\n"
                      f"- 当前存活的玩家有：{alive_players_str}\n"
                      f"- 目前的发言记录如下：\n---\n{history_str}\n---\n\n"
                      f"=== 你的任务 ===\n"
                      f"请综合以上所有信息，扮演好你的角色并发表观点。你的目标是：\n"
                      f"- 如果你是好人阵营（村民、预言家、女巫、猎人），你需要找出并投票淘汰狼人。\n"
                      f"- 如果你是狼人阵营，你需要伪装自己，误导好人，并保护你的狼人队友。\n"
                      f"请直接给出你的发言，不要包含任何思考过程或分析。")
            
            # 【新功能】记录Prompt
            prompt_logger.add_prompt(
                title=f"为 {agent.name} ({ROLE_CN_MAP.get(player_role, player_role)}) 生成白天发言的Prompt",
                prompt=prompt
            )
            # 【修复】统一使用静默回复，避免直接打印思考过程
            response_msg = await self._get_silent_reply(agent, prompt)
            
            # 【修复】使用新的健壮解析函数
            raw_response = self._parse_ai_response(response_msg.content)
            
            # 对AI的回复进行后处理，移除思考过程
            cleaned_content = raw_response
            if not getattr(agent, 'is_user', False):
                # 【修复】更智能地移除思考过程，保留完整发言
                
                # 首先移除明确的思考标记
                cleaned_content = re.sub(r"^\(thinking\):", "", cleaned_content, flags=re.IGNORECASE).strip()
                
                # 处理可能的格式："思考过程... Player_X: 实际发言内容"
                if f"{agent.name}:" in cleaned_content:
                    parts = cleaned_content.split(f"{agent.name}:")
                    if len(parts) > 1:
                        # 检查分割后的第一部分是否主要是思考内容
                        first_part = parts[0].strip().lower()
                        thinking_indicators = ['thinking', 'strategy', '策略', '分析', '我需要', '考虑', '想法', 'player_' + agent.name.split('_')[1] + '(thinking)']
                        
                        # 如果第一部分包含大量思考关键词，或明显是思考过程，则移除
                        if (len(first_part) > 100 and any(indicator in first_part for indicator in thinking_indicators)) or \
                           '(thinking)' in first_part:
                            # 取最后一个 "Player_X:" 之后的内容
                            cleaned_content = parts[-1].strip()
                        else:
                            # 否则保留完整内容，只是去掉重复的玩家名前缀
                            cleaned_content = f"{agent.name}:" + ":".join(parts[1:])
                            cleaned_content = cleaned_content.replace(f"{agent.name}:", "", 1).strip()
                
                # 处理段落级别的思考内容移除
                paragraphs = [p.strip() for p in cleaned_content.split('\n\n') if p.strip()]
                if len(paragraphs) > 1:
                    first_para = paragraphs[0].lower()
                    thinking_keywords = ['thinking', 'strategy', '策略', '分析：', '我的想法是', '我需要考虑', '当前局面']
                    # 只有当第一段明确是思考内容且较长时才移除
                    if len(first_para) > 80 and any(keyword in first_para for keyword in thinking_keywords):
                        cleaned_content = "\n\n".join(paragraphs[1:])
                    else:
                        cleaned_content = "\n\n".join(paragraphs)
                else:
                    cleaned_content = "\n\n".join(paragraphs)

            # 记录并广播发言
            speech = f"玩家 {agent.name} 说: {cleaned_content}"
            
            # 【新增】获取模型信息并记录到日志
            model_info = self._get_agent_model_info(agent)
            game_logger.add_entry(f"[{agent.name} 发言 - {model_info}]: {cleaned_content}")
            
            # 【修复】手动打印处理干净的发言
            print(speech)
            print("\n") # 添加两行空行

            self.game_state["discussion_history"].append(speech)
            # 【新功能】将发言记录到长期历史中
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-发言]: {agent.name} 说: {cleaned_content}")
            game_logger.add_entry(speech)
            # 玩家发言是公开信息，手动打印后，只需广播，不再重复打印
            await self._announce_to_public(speech, role="user", to_print=False)

        await self._announce_to_public("所有玩家发言结束。", role="system")

    async def _vote_phase(self) -> None:
        self.game_state["phase"] = "VOTE"
        await self._announce_to_public("现在进入投票环节。请投票选出你认为的狼人。若无明确选择，可以输入 '弃票' 表示本轮弃票。", role="system")

        alive_players_data = self._get_alive_players_by_role()
        potential_targets = [p["agent"].name for p in alive_players_data]

        # 分离用户和AI玩家，以串行方式处理投票，避免并发I/O冲突
        user_voters = [p["agent"] for p in alive_players_data if getattr(p["agent"], 'is_user', False)]
        ai_voters = [p["agent"] for p in alive_players_data if not getattr(p["agent"], 'is_user', False)]
        
        votes = []

        # 1. 首先，串行收集所有AI的投票
        for voter in ai_voters:
            try:
                # 为每个AI的投票任务增加超时
                vote_result = await asyncio.wait_for(self._collect_vote(voter, potential_targets), timeout=30.0)
                votes.append(vote_result)
            except Exception as e:
                game_logger.add_entry(f"[{voter.name} 投票超时或出错]: {e}")
                votes.append((voter.name, None)) # 计为弃票

        # 2. 然后，收集所有人类玩家的投票
        for voter in user_voters:
            # 人类玩家没有超时
            vote_result = await self._collect_vote(voter, potential_targets)
            votes.append(vote_result)

        # 3. 计票和公布投票详情
        vote_details = []
        for voter_name, target_name in votes:
            if target_name:
                detail = f"{voter_name} 投票给 -> {target_name}"
            else:
                detail = f"{voter_name} 弃票"
            vote_details.append(detail)
        
        # 在控制台打印每一票的详情
        print("\n--- 投票详情 ---")
        for detail in vote_details:
            print(detail)
        print("------------------\n")

        vote_counter = Counter(vote for _, vote in votes if vote)
        log_entry = f"投票统计: {dict(vote_counter)}"
        game_logger.add_entry(log_entry)
        await self._announce_to_public(log_entry, role="system", to_print=True)

        if not vote_counter:
            log_entry = "无人投票，本轮平票。"
            game_logger.add_entry(log_entry)
            await self._announce_to_public(log_entry, role="system", to_print=True)
            return

        max_votes = max(vote_counter.values())
        most_voted_players = [p for p, v in vote_counter.items() if v == max_votes]

        # 处理平票
        if len(most_voted_players) > 1:
            log_entry = f"出现平票 ({', '.join(most_voted_players)})，本轮无人出局。"
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-投票]: {log_entry}")
            game_logger.add_entry(log_entry)
            await self._announce_to_public(log_entry, role="system", to_print=True)
        else:
            voted_out_player_name = most_voted_players[0]
            self.game_state["players"][voted_out_player_name]["status"] = "dead"
            self.game_state["night_info"]["death_cause"][voted_out_player_name] = "vote"  # 记录死因
            log_entry = f"投票结果：玩家 {voted_out_player_name} 被淘汰。"
            # 【新功能】将投票结果记录到长期历史中
            vote_details_str = ", ".join([f"{voter}->{target}" for voter, target in votes if target])
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-投票]: {log_entry} (详情: {vote_details_str})")
            game_logger.add_entry(log_entry)
            await self._announce_to_public(log_entry, role="system", to_print=True)
            
            # 确保在宣布淘汰后立即处理遗言
            eliminated_player_data = self.game_state["players"][voted_out_player_name]
            await self._handle_last_words([eliminated_player_data])
        
        self._check_win_condition()
        
        # 【新增】投票阶段结束后，为所有存活玩家更新记忆摘要
        # 确保进入夜晚时能获取到完整的白天信息（发言、投票、遗言、猎人开枪等）
        if not self.game_state["game_over"]:
            await self._update_all_players_memory_for_night()

    async def _collect_vote(self, voter: AgentBase, potential_targets: List[str]) -> Tuple[str, Optional[str]]:
        """辅助函数：向单个玩家收集投票，增强了对用户和AI输入的兼容性"""
        target_name = None
        if getattr(voter, 'is_user', False):
            # 针对人类玩家的优化输入
            while target_name is None:
                prompt = (f"请从以下玩家中投票选择一人淘汰：\n{', '.join(potential_targets)}\n"
                          f"请输入你要投票的玩家姓名或编号；若无明确选择，请输入 '弃票' / 'abstain' 表示弃票：")
                response_msg = await voter.reply(Msg(self.name, prompt, role="user"))
                user_input = response_msg.content.strip().lower() if response_msg.content else ""

                for p_target in potential_targets:
                    player_id = p_target.split('_')[-1]
                    if user_input == p_target.lower() or \
                       user_input == f"player{player_id}" or \
                       user_input == f"player {player_id}" or \
                       user_input == player_id:
                        target_name = p_target
                        break
                
                # 支持弃票
                if not target_name and user_input in ['弃票','abstain','pass','skip','不投','不投票']:
                    return voter.name, None

                if not target_name:
                    await voter.observe(Msg(self.name, "无效的输入，请重新输入。", role="system"))
            
            # 【修复】为用户投票添加日志记录
            game_logger.add_entry(f"[{voter.name} 投票给]: {target_name}")
            return voter.name, target_name
        else:
            # 【Prompt优化】为AI投票提供完整的上下文
            current_day = self.game_state['day']
            player_role = self.game_state["identities"][voter.name]

            # 1. 构建私密信息部分 (与发言环节逻辑相同)
            private_info = "你是一个普通村民，没有特殊信息。"
            if player_role == "seer":
                seer_history = [log for log in self.game_state["full_history"] if "查验了" in log and voter.name in log]
                if seer_history:
                    private_info = "你的查验历史如下：\n" + "\n".join(seer_history)
                else:
                    private_info = "你还没有查验过任何人。"
            elif player_role == "witch":
                save_status = "可用" if self.game_state["witch_potions"]["save"] else "已用"
                poison_status = "可用" if self.game_state["witch_potions"]["poison"] else "已用"
                private_info = f"你的药剂状态：解药[{save_status}]，毒药[{poison_status}]。"
            elif player_role == "werewolf":
                werewolf_teammates = [p_name for p_name, p_role in self.game_state["identities"].items() if p_role == "werewolf" and p_name != voter.name]
                teammates_info = ""
                if werewolf_teammates:
                    teammates_info = f"你的狼人队友是: {', '.join(werewolf_teammates)}。\n"
                else:
                    teammates_info = "你的狼人队友已经死亡，你现在是唯一的狼人。\n"
                
                # 【新增】狼人击杀历史
                werewolf_history = [log for log in self.game_state["full_history"] if "狼人团队决定淘汰" in log or "狼人代表未能提供有效目标" in log]
                if werewolf_history:
                    kill_history = "你们的击杀历史如下：\n" + "\n".join(werewolf_history)
                else:
                    kill_history = "你们还没有执行任何击杀行动。"
                
                private_info = teammates_info + kill_history
            
            # 2. 构建完整的Prompt
            discussion_summary = "\n".join(self.game_state["discussion_history"])
            memory_summary = self._get_player_memory(voter.name)
            
            prompt = (f"现在是第 {current_day} 天的投票环节。\n"
                      f"你是 {voter.name}，你的身份是【{ROLE_CN_MAP.get(player_role, player_role)}】。\n\n"
                      f"=== 你的私密信息 ===\n{private_info}\n\n"
                      f"=== 游戏至今的记忆摘要 ===\n{memory_summary}\n\n"
                      f"=== 今天白天的发言回顾 ===\n{discussion_summary}\n\n"
                      f"=== 你的任务 ===\n"
                      f"根据以上所有信息，从下列存活玩家中投票淘汰一人：\n[{', '.join(potential_targets)}]\n"
                      f"你的回复必须严格遵循 '我投票给: [玩家姓名]' 的格式，不要包含任何其他内容或思考过程。\n"
                      f"如果你想弃票，请仅回复：弃票。")

            # 增加重试逻辑
            for attempt in range(2): # 最多尝试2次
                try:
                    # 【新功能】记录Prompt
                    prompt_logger.add_prompt(
                        title=f"向 {voter.name} 提问投票目标 (尝试 {attempt + 1})",
                        prompt=prompt
                    )
                    response_msg = await self._get_silent_reply(voter, prompt)
                    # 【修复】使用新的健壮解析函数
                    raw_response = self._parse_ai_response(response_msg.content)
                    
                    # 【新增】获取模型信息并记录到日志
                    model_info = self._get_agent_model_info(voter)
                    game_logger.add_entry(f"[{voter.name} 投票回复 (尝试 {attempt + 1}) - {model_info}]: {raw_response}")

                    # 解析是否为弃票（支持多种同义词）
                    normalized = raw_response.strip().lower() if raw_response else ""
                    if any(token in normalized for token in ['弃票','abstain','pass','skip','不投','不投票']):
                        game_logger.add_entry(f"[{voter.name} 弃票]")
                        return voter.name, None

                    # 【最终修复方案】采用最稳健的解析方式：直接在原始回复中搜索有效的玩家名字
                    # 从后向前搜索，以正确匹配 Player_10 而不是 Player_1
                    for p_target in sorted(potential_targets, key=len, reverse=True):
                        if p_target in raw_response:
                            game_logger.add_entry(f"[{voter.name} 投票给]: {p_target}")
                            return voter.name, p_target
                except Exception as e:
                    game_logger.add_entry(f"[{voter.name} 投票时出现异常 (尝试 {attempt + 1})]: {e}")
            
            # 如果所有尝试都失败，则视为弃票
            game_logger.add_entry(f"[{voter.name} 弃票 (多次尝试失败)]")
            return voter.name, None

    async def _handle_last_words(self, dead_players_data: List[Dict]) -> None:
        """处理被淘汰玩家的遗言环节"""
        if not dead_players_data:
            return
            
        for player_data in dead_players_data:
            agent = player_data["agent"]
            await self._announce_to_public(f"玩家 {agent.name} 被淘汰，现在是他的遗言时间。", role="system", to_print=True)
            
            prompt = "你已经被淘汰了。这是你的遗言环节，请根据你掌握的所有信息，发表你的最后一段发言，可以尝试为好人阵营提供帮助。"
            if isinstance(agent, UserAgent):
                prompt = "你已被投票出局，请发表你的遗言："
            else:
                # 为AI构建更丰富的遗言prompt
                player_role = self.game_state["identities"][agent.name]
                memory_summary = self._get_player_memory(agent.name)
                discussion_summary = "\n".join(self.game_state["discussion_history"])

                # 构建私密信息
                private_info = "你是一个普通村民，没有特殊信息。"
                if player_role == "seer":
                    seer_history = [log for log in self.game_state["full_history"] if "查验了" in log and agent.name in log]
                    if seer_history:
                        private_info = "你的查验历史如下：\n" + "\n".join(seer_history)
                    else:
                        private_info = "你还没有查验过任何人。"
                elif player_role == "witch":
                    save_status = "可用" if self.game_state["witch_potions"]["save"] else "已用"
                    poison_status = "可用" if self.game_state["witch_potions"]["poison"] else "已用"
                    private_info = f"你的药剂状态：解药[{save_status}]，毒药[{poison_status}]。"
                elif player_role == "werewolf":
                    werewolf_teammates = [p_name for p_name, p_role in self.game_state["identities"].items() if p_role == "werewolf" and p_name != agent.name]
                    teammates_status = [f"{name}({self.game_state['players'][name]['status']})" for name in werewolf_teammates]
                    teammates_info = ""
                    if werewolf_teammates:
                        teammates_info = f"你的狼人队友状态: {', '.join(teammates_status)}。\n"
                    else:
                        teammates_info = "你是唯一的狼人。\n"
                    
                    # 【新增】狼人击杀历史
                    werewolf_history = [log for log in self.game_state["full_history"] if "狼人团队决定淘汰" in log or "狼人代表未能提供有效目标" in log]
                    if werewolf_history:
                        kill_history = "你们的击杀历史如下：\n" + "\n".join(werewolf_history)
                    else:
                        kill_history = "你们还没有执行任何击杀行动。"
                    
                    private_info = teammates_info + kill_history

                # 根据身份动态构建任务说明
                task_instruction = ""
                if player_role == "werewolf":
                    # 狼人遗言：只提示可以继续迷惑
                    task_instruction = (
                        f"请综合以上所有信息，发表你的最后一段发言。\n"
                        f"{'注意：你是第一天晚上被淘汰的，没有任何游戏信息，请基于你的身份和推测合理发言。' if self.game_state['day'] == 1 else ''}"
                        f"请尽量隐藏自己和队友的身份，你可以继续迷惑好人，为你的队友争取优势。\n"
                        f"请直接给出你的发言，不要包含任何思考过程。"
                    )
                else:
                    # 好人阵营遗言：只提示为好人阵营提供帮助
                    task_instruction = (
                        f"请综合以上所有信息，发表你的最后一段发言。\n"
                        f"{'注意：你是第一天晚上被淘汰的，没有任何游戏信息，请基于你的身份和推测合理发言。' if self.game_state['day'] == 1 else ''}"
                        f"请尽力为好人阵营提供有价值的线索和分析。\n"
                        f"请直接给出你的发言，不要包含任何思考过程。"
                    )

                prompt = (
                    f"你已经被淘汰了。现在是第 {self.game_state['day']} 天的遗言环节。\n"
                    f"你是 {agent.name}，你的身份是【{ROLE_CN_MAP.get(player_role, player_role)}】。\n\n"
                    f"=== 你的私密信息 ===\n{private_info}\n\n"
                    f"=== 游戏至今的记忆摘要 ===\n{memory_summary if memory_summary else '(第一天没有历史信息)'}\n\n"
                    f"=== 导致你出局的当天发言回顾 ===\n{discussion_summary if discussion_summary else '(第一天晚上被淘汰，没有发言记录)'}\n\n"
                    f"=== 你的任务 ===\n"
                    f"{task_instruction}"
                )

            # 【修复】统一使用静默回复，并为遗言环节增加超时
            try:
                # 【新功能】记录Prompt
                prompt_logger.add_prompt(
                    title=f"为 {agent.name} (已淘汰) 生成遗言的Prompt",
                    prompt=prompt
                )
                response_msg = await asyncio.wait_for(self._get_silent_reply(agent, prompt), timeout=30.0)
            except asyncio.TimeoutError:
                game_logger.add_entry(f"[{agent.name} 发表遗言超时]")
                response_msg = Msg(agent.name, "...", role="assistant") # 使用默认遗言
            
            # 【修复】使用新的健壮解析函数
            raw_response = self._parse_ai_response(response_msg.content)

            # 【修复】同样对遗言进行后处理，与发言逻辑保持一致
            cleaned_content = raw_response
            if not getattr(agent, 'is_user', False):
                # 【修复】更智能地移除思考过程，保留完整发言
                
                # 首先移除明确的思考标记
                cleaned_content = re.sub(r"^\(thinking\):", "", cleaned_content, flags=re.IGNORECASE).strip()
                
                # 处理可能的格式："思考过程... Player_X: 实际遗言内容"
                if f"{agent.name}:" in cleaned_content:
                    parts = cleaned_content.split(f"{agent.name}:")
                    if len(parts) > 1:
                        # 检查分割后的第一部分是否主要是思考内容
                        first_part = parts[0].strip().lower()
                        thinking_indicators = ['thinking', 'strategy', '策略', '分析', '我需要', '考虑', '想法', 'player_' + agent.name.split('_')[1] + '(thinking)']
                        
                        # 如果第一部分包含大量思考关键词，或明显是思考过程，则移除
                        if (len(first_part) > 100 and any(indicator in first_part for indicator in thinking_indicators)) or \
                           '(thinking)' in first_part:
                            # 取最后一个 "Player_X:" 之后的内容
                            cleaned_content = parts[-1].strip()
                        else:
                            # 否则保留完整内容，只是去掉重复的玩家名前缀
                            cleaned_content = f"{agent.name}:" + ":".join(parts[1:])
                            cleaned_content = cleaned_content.replace(f"{agent.name}:", "", 1).strip()
                
                # 处理段落级别的思考内容移除
                paragraphs = [p.strip() for p in cleaned_content.split('\n\n') if p.strip()]
                if len(paragraphs) > 1:
                    first_para = paragraphs[0].lower()
                    thinking_keywords = ['thinking', 'strategy', '策略', '分析：', '我的想法是', '我需要考虑', '当前局面']
                    # 只有当第一段明确是思考内容且较长时才移除
                    if len(first_para) > 80 and any(keyword in first_para for keyword in thinking_keywords):
                        cleaned_content = "\n\n".join(paragraphs[1:])
                    else:
                        cleaned_content = "\n\n".join(paragraphs)
                else:
                    cleaned_content = "\n\n".join(paragraphs)

            # 广播遗言
            last_words = f"玩家 {agent.name} 的遗言是：{cleaned_content}"
            
            # 【新增】获取模型信息并记录到日志
            model_info = self._get_agent_model_info(agent)
            game_logger.add_entry(f"[{agent.name} 遗言 - {model_info}]: {cleaned_content}")
            
            # 【修复】手动打印处理干净的遗言
            print(last_words)

            # 【新功能】将遗言记录到长期历史中
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-遗言]: {agent.name} 说: {cleaned_content}")
            game_logger.add_entry(last_words)
            # 遗言是公开信息，手动打印后，只需广播，不再重复打印
            await self._announce_to_public(last_words, role="system", to_print=False)
            
            # 【新功能】处理猎人开枪
            await self._handle_hunter_shoot(agent.name)

    async def _handle_hunter_shoot(self, dead_player_name: str) -> None:
        """【新功能】处理猎人开枪机制"""
        # 检查死者是否是猎人
        if self.game_state["identities"][dead_player_name] != "hunter":
            return
        
        # 检查死因，如果是被女巫毒杀，不能开枪
        death_cause = self.game_state["night_info"]["death_cause"].get(dead_player_name, "vote")
        if death_cause == "poison":
            await self._announce_to_public(f"猎人 {dead_player_name} 被毒杀，无法开枪。", role="system", to_print=True)
            game_logger.add_entry(f"猎人 {dead_player_name} 被毒杀，无法开枪。")
            return
        
        # 猎人可以开枪
        await self._announce_to_public(f"猎人 {dead_player_name} 触发开枪技能！", role="system", to_print=True)
        
        hunter_agent = self.game_state["players"][dead_player_name]["agent"]
        alive_players_data = self._get_alive_players_by_role()
        potential_targets = [p["agent"].name for p in alive_players_data]
        
        # 【调试】显示可选目标
        game_logger.add_entry(f"[猎人开枪]: 可选目标列表 = {potential_targets}")
        
        if not potential_targets:
            return
        
        # 【优化】获取猎人的记忆摘要
        memory_summary = self._get_player_memory(dead_player_name)
        discussion_summary = "\n".join(self.game_state["discussion_history"])
        
        target_name = None
        prompt = (
            f"你是 {dead_player_name}，你的身份是【{ROLE_CN_MAP['hunter']}】，你已被淘汰。现在你可以开枪带走一名玩家。\n\n"
            f"=== 游戏至今的记忆摘要 ===\n{memory_summary}\n\n"
            f"=== 当天的发言回顾 ===\n{discussion_summary}\n\n"
            f"=== 你的任务 ===\n"
            f"请从以下存活玩家中选择一人开枪带走：\n{', '.join(potential_targets)}\n"
            f"综合考虑所有信息，选择你认为最可能是狼人的玩家。\n"
            f"请以'我开枪带走: [玩家姓名]'的格式回复。若不想开枪请输入 '弃票'。"
        )
        
        if getattr(hunter_agent, 'is_user', False):
            prompt = f"你是猎人，可以开枪带走一名玩家。请从以下玩家中选择：\n{', '.join(potential_targets)}\n"
            prompt += "请输入你要开枪带走的玩家姓名或编号；若不想开枪请输入 '弃票'。"
        
        for attempt in range(3):  # 最多尝试3次
            prompt_logger.add_prompt(
                title=f"向 {dead_player_name} (猎人) 提问开枪目标 (尝试 {attempt + 1})",
                prompt=prompt
            )
            
            response_msg = await self._get_silent_reply(hunter_agent, prompt)
            raw_response = self._parse_ai_response(response_msg.content)
            
            # 【新增】获取模型信息并记录到日志
            model_info = self._get_agent_model_info(hunter_agent)
            game_logger.add_entry(f"[{dead_player_name} 猎人开枪回复 (尝试 {attempt + 1}) - {model_info}]: {raw_response}")
            
            # 解析目标：支持直接命中、格式化的 '我开枪带走: Player_X'，以及嵌套JSON或被引号包裹的情况
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
            
            # 【调试】记录解析过程
            game_logger.add_entry(f"[猎人开枪解析]: 原始回复='{raw_response}', 处理后='{parsed_candidate}'")
            
            # 检查是否为弃票
            norm = parsed_candidate.strip().lower()
            if any(tok in norm for tok in ['弃票','abstain','pass','skip','不想','不投']):
                game_logger.add_entry(f"[{dead_player_name} 弃枪]")
                return
            
            # 增强匹配逻辑，支持更多格式
            for p_target in potential_targets:
                player_id = p_target.split('_')[-1]
                normalized_input = parsed_candidate.lower().strip()
                
                # 支持的格式：Player_6, player_6, player6, player 6, 6
                if normalized_input == p_target.lower() or \
                   normalized_input == f"player_{player_id}" or \
                   normalized_input == f"player{player_id}" or \
                   normalized_input == f"player {player_id}" or \
                   normalized_input == f"player-{player_id}" or \
                   normalized_input == player_id or \
                   p_target.lower() in normalized_input:
                    target_name = p_target
                    game_logger.add_entry(f"[猎人开枪匹配成功]: '{normalized_input}' 匹配到 '{p_target}'")
                    break
            
            # 如果上面没匹配到，再检查是否直接在原始输入中出现目标名
            if not target_name:
                for p_target in sorted(potential_targets, key=len, reverse=True):
                    if p_target in raw_response:
                        target_name = p_target
                        game_logger.add_entry(f"[猎人开枪备用匹配成功]: 在原始回复中找到 '{p_target}'")
                        break
            
            # 【关键修复】如果找到了有效目标，立即跳出外层循环
            if target_name:
                game_logger.add_entry(f"[猎人开枪]: 找到有效目标 '{target_name}'，停止尝试")
                break
        
        if target_name:
            self.game_state["players"][target_name]["status"] = "dead"
            log_entry = f"猎人 {dead_player_name} 开枪带走了 {target_name}。"
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-猎人开枪]: {log_entry}")
            game_logger.add_entry(log_entry)
            await self._announce_to_public(log_entry, role="system", to_print=True)
            
            # 被枪杀的玩家的遗言处理
            shot_player_data = self.game_state["players"][target_name]
            
            # 【新增】判断猎人开枪时的遗言规则
            # 如果是第二夜及之后，且触发开枪的猎人是因夜晚死亡，则被带走的玩家无遗言
            # 如果是首夜或白天投票死亡触发的猎人开枪，则被带走的玩家有遗言
            hunter_death_cause = self.game_state["night_info"]["death_cause"].get(dead_player_name)
            
            if self.game_state["day"] >= 2 and hunter_death_cause in ["werewolf", "poison"]:
                # 第二夜及之后，因夜晚死亡的猎人开枪带走的玩家无遗言
                game_logger.add_entry(f"[遗言规则]: {target_name} 被夜晚死亡的猎人带走，无遗言权")
                await self._announce_to_public(f"根据游戏规则，{target_name} 被夜晚死亡的猎人带走，无遗言。", role="system", to_print=True)
            else:
                # 首夜死亡或白天投票死亡触发的猎人开枪，被带走的玩家有遗言
                await self._handle_last_words([shot_player_data])
            
            # 如果被枪杀的也是猎人，形成连锁反应（递归调用）
            # 注意：为防止无限递归，实际规则中通常猎人被猎人枪杀不能再开枪
            # 这里我们采用标准规则：被猎人枪杀的猎人不能再开枪
        else:
            # 如果多次都无法给出有效目标，随机选择
            game_logger.add_entry(f"[猎人开枪匹配失败]: 3次尝试都未能匹配到有效目标")
            fallback_target = random.choice(potential_targets)
            self.game_state["players"][fallback_target]["status"] = "dead"
            log_entry = f"猎人 {dead_player_name} 未能提供有效目标，裁判随机选择了 {fallback_target}。"
            self.game_state["full_history"].append(f"[第{self.game_state['day']}天-猎人开枪]: {log_entry}")
            game_logger.add_entry(log_entry)
            await self._announce_to_public(log_entry, role="system", to_print=True)
        
        # 检查胜负
        self._check_win_condition()

    def _check_win_condition(self) -> None:
        """【新功能】实现真正的胜利条件判断（包含猎人）"""
        alive_werewolves = len(self._get_alive_players_by_role("werewolf"))
        alive_good_guys = len(self._get_alive_players_by_role(["villager", "seer", "witch", "hunter"]))

        if alive_werewolves == 0:
            self.game_state["game_over"] = True
            self.game_state["winner"] = "好人阵营"
        elif alive_good_guys == 0:
            self.game_state["game_over"] = True
            self.game_state["winner"] = "狼人阵营"

    def _get_night_summary(self) -> str:
        """生成夜晚结果的公开摘要"""
        deaths = []
        killed_by_werewolf = self.game_state["night_info"].get("killed_by_werewolf")
        poisoned = self.game_state["night_info"].get("poisoned")
        saved = self.game_state["night_info"].get("saved")

        if killed_by_werewolf and not saved:
            deaths.append(killed_by_werewolf)
        
        if poisoned and poisoned not in deaths:
            deaths.append(poisoned)

        if not deaths:
            return "昨晚是平安夜。"
        else:
            return f"昨晚，玩家 {', '.join(deaths)} 被淘汰了。"

    async def _announce_to_public(self, content: str, role: str = "user", to_print: bool = True) -> None:
        """【更新】向所有玩家广播裁判公告, to_print 控制是否在裁判控制台打印"""
        if to_print:
            print(f"\n[裁判公告]: {content}") # 在公告前增加换行
        # 使用 public_channel 确保所有 Agent (包括 UserAgent) 都能“听到”
        msg = Msg(self.name, content, role=role)
        await self.public_channel.broadcast(msg)
            
    # --- 辅助函数 ---
    def _get_alive_players_by_role(self, roles: Optional[Union[str, List[str]]] = None) -> List[Dict]:
        """根据角色获取所有存活的玩家列表"""
        if roles and isinstance(roles, str):
            roles = [roles]
            
        alive_players = []
        for name, data in self.game_state["players"].items():
            if data["status"] == "alive":
                if not roles or self.game_state["identities"][name] in roles:
                                       alive_players.append(data)
        return alive_players
        
    # async def reply(self, x: Msg = None) -> Msg:
    #     """【修复崩溃】裁判自身也需要一个异步的reply方法来调用模型生成摘要"""
    #     # _get_silent_reply 期望一个异步的 a-waitable reply 方法
    #     # 我们直接调用模型的 __call__ 方法，它是异步的
    #     # 【最终修复】OpenAI模型封装器期望接收一个包含字典的列表，而不是纯字符串。
    #     # 我们需要手动构建这个列表。
    #     messages = [{"role": "user", "content": x.content}]
    #     return await self.model(messages)

    async def _announce_game_setup(self) -> None:
        """【新功能】在游戏开始时广播一次游戏配置"""
        await self._announce_to_public(self.game_initial_info, role="system", to_print=True)

    async def observe(self, x: Msg) -> None:
        """
        GameMasterAgent作为游戏控制器，它主动发出消息，但不需要“观察”自己或其他玩家的广播。
        实现一个空的observe可以防止在某些MsgHub配置下（如果它被意外加入到某个hub中）因未实现该方法而报错。
        """
        pass

    async def _update_all_players_memory_for_night(self) -> None:
        """
        【新增】在夜晚开始前为所有存活玩家更新记忆摘要。
        确保夜晚行动时能获取到完整的上一天信息（发言、投票、遗言、猎人开枪等）。
        """
        alive_players_data = self._get_alive_players_by_role()
        
        for player_data in alive_players_data:
            player_name = player_data["agent"].name
            try:
                # 为每个玩家生成最新的记忆摘要
                await self._generate_memory_summary(player_name)
                game_logger.add_entry(f"[夜晚前更新记忆]: 为 {player_name} 更新记忆摘要完成")
            except Exception as e:
                game_logger.add_entry(f"[夜晚前更新记忆失败]: {player_name} - {e}")

    async def _generate_memory_summary(self, player_name: str, for_morning: bool = False, current_discussion: list = None) -> str:
        """
        【逻辑重构】实现增量式记忆摘要
        
        Args:
            player_name: 玩家名称
            for_morning: 是否是白天发言前生成摘要
            current_discussion: 当天已经发生的发言列表（只在白天发言时使用）
        """
        player_data = self.game_state["players"][player_name]
        previous_summary = player_data.get("memory_summary", "这是游戏的初始阶段，还没有历史记忆。")

        # 【修复】根据调用场景确定需要包含的事件范围
        current_day = self.game_state['day']
        
        if for_morning:
            # ===== 白天发言前生成摘要 =====
            # 包含：昨晚的公开结果 + 当天之前的玩家发言
            
            # 1. 昨晚的公开结果（死亡信息）
            night_events = [
                log for log in self.game_state["full_history"] 
                if f"[第{current_day}天-夜晚]" in log
            ]
            
            # 2. 当天之前的玩家发言
            today_discussion = current_discussion if current_discussion else []
            
            # 合并事件
            new_events = night_events + today_discussion
            context_desc = f"昨晚（第{current_day}天夜晚）的结果 + 今天之前的发言"
            
        else:
            # ===== 夜晚前更新记忆 =====
            # 收集当天完整的白天信息（发言、投票、遗言等）
            new_events = [
                log for log in self.game_state["full_history"] 
                if f"[第{current_day}天" in log
            ]
            context_desc = f"第{current_day}天已发生的所有事件"
        
        if not new_events:
            # 如果没有新事件，直接返回上一份摘要
            return previous_summary

        # 【关键修复】确保包含所有关键事件类型
        # 注意：discussion_history 中的发言格式是 "玩家 Player_X 说: ..."，不包含"发言"关键词
        # 所以需要区分处理
        important_events = []
        for event in new_events:
            # 如果是 full_history 中的事件，需要过滤
            if event.startswith("[第"):
                # 过滤重要事件：投票、淘汰、遗言、猎人开枪、夜晚死亡
                if any(keyword in event for keyword in [
                    "发言", "投票", "被淘汰", "遗言", "猎人开枪", "被淘汰了", 
                    "触发开枪技能", "开枪带走", "平安夜"
                ]):
                    important_events.append(event)
            else:
                # 如果是 discussion_history 中的发言，直接保留
                important_events.append(event)
        
        events_str = "\n".join(important_events) if important_events else "\n".join(new_events)

        prompt = (
            f"你是一名狼人杀游戏的中立记录员。你的任务是根据以往记忆和新发生的事件，生成一份更新后的、简洁的全局回顾。\n"
            f"回顾应严格遵循事实，按时间顺序或关键事件（如投票、淘汰、重要发言、猎人开枪）来组织。\n"
            f"请不要包含任何主观分析、猜测或行动建议。\n"
            f"请将新旧信息整合成一个连贯的、不超过350字的摘要。\n\n"
            f"=== 以往记忆 ===\n{previous_summary}\n\n"
            f"=== {context_desc} ===\n{events_str}\n\n"
            f"=== 你的客观回顾（更新版） ==="
        )
        
        try:
            # 【新功能】记录Prompt到常规日志
            prompt_logger.add_prompt(
                title=f"为 {player_name} 生成记忆摘要的Prompt",
                prompt=prompt
            )
            # 【修改】使用专门的摘要模型而不是裁判的主模型
            # 创建一个临时的"摘要生成代理"，使用摘要模型
            new_summary = await self._call_summary_model(prompt)
            
            # 【新增】如果是夜晚前更新记忆，记录到专门的夜晚记忆日志（实时写入）
            # not for_morning 表示是夜晚前更新，而不是白天发言前更新
            if not for_morning:
                memory_logger.add_memory_update(player_name, prompt, new_summary)
            
            # 更新该玩家的记忆状态
            self.game_state["players"][player_name]["memory_summary"] = new_summary
            
            return new_summary
        except Exception as e:
            game_logger.add_entry(f"[摘要生成失败]: {e}")
            return "记忆模块处理异常，请自行判断。"

    def _get_player_memory(self, player_name: str) -> str:
        """【优化】统一获取玩家记忆摘要的辅助函数"""
        return self.game_state["players"][player_name].get("memory_summary", "这是游戏的初始阶段，还没有历史记忆。")

    async def _call_summary_model(self, prompt: str) -> str:
        """
        调用专门的摘要模型生成摘要。
        使用与投票/发言相同的简单逻辑。
        """
        try:
            # 创建一个临时的"摘要生成代理"，使用摘要模型
            summary_agent = ReActAgent(
                name="Summary_Generator",
                sys_prompt="你是一名狼人杀游戏的中立记录员。",
                model=self.summary_model,
                max_iters=1,
                formatter=OpenAIMultiAgentFormatter(),
            )
            
            # 使用和其他Agent一样的方式调用
            response_msg = await self._get_silent_reply(summary_agent, prompt)
            content = self._parse_ai_response(response_msg.content)
            
            return content
            
        except Exception as e:
            error_msg = str(e)
            game_logger.add_entry(f"[摘要模型调用失败]: {error_msg}")
            return "记忆模块处理异常，请自行判断。"

