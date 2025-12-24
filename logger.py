import os
import datetime
from typing import Dict, List

class GameLogger:
    def __init__(self) -> None:
        self.log_entries = []
        self.log_filename = ""

    def start_game(self, identities: Dict[str, str]):
        self.log_entries = []
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"game_log_{timestamp}.txt"
        
        self.log_entries.append("===== 游戏开始 =====")
        self.log_entries.append("角色分配 (上帝视角):")
        for name, role in identities.items():
            self.log_entries.append(f"- {name}: {role}")
        self.log_entries.append("====================\n")

    def add_entry(self, entry: str, to_console: bool = False):
        if to_console:
            print(entry)
        self.log_entries.append(entry)
        self._flush_entry(entry)

    def _flush_entry(self, entry: str):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        with open(os.path.join(log_dir, self.log_filename), "a", encoding="utf-8") as f:
            f.write(entry + "\n")

    def log_identities_at_end(self, identities: Dict[str, str]):
        """在游戏结束时记录所有玩家的最终身份。"""
        self.add_entry("\n===== 游戏结束 - 最终身份揭晓 =====")
        for name, role in identities.items():
            self.add_entry(f"- {name}: {role}")
        self.add_entry("====================================\n")

    def save_log(self):
        # 这个方法可以保留，以防万一有最终保存的需求，或者简单地pass掉
        print(f"\n游戏日志已保存至: logs/{self.log_filename}")

# 创建一个全局的logger实例，方便在其他模块中导入和使用
game_logger = GameLogger()


class PromptLogger:
    """一个专门用于记录发送给AI的Prompt的日志记录器。"""
    def __init__(self) -> None:
        self.log_filename = ""

    def start_logging(self) -> None:
        """初始化日志文件。"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"prompt_log_{timestamp}.txt"
        
        # 确保logs目录存在
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def add_prompt(self, title: str, prompt: str) -> None:
        """
        记录一个prompt到日志文件。

        Args:
            title (str): 这次AI调用的说明 (e.g., "为Player_1生成发言prompt").
            prompt (str): 发送给AI的完整prompt.
        """
        if not self.log_filename:
            self.start_logging()
            
        log_dir = "logs"
        log_entry = (
            f"===== {title} =====\n"
            f"{prompt}\n"
            f"===== END =====\n\n"
        )
        
        with open(os.path.join(log_dir, self.log_filename), "a", encoding="utf-8") as f:
            f.write(log_entry)

# 创建一个全局的prompt logger实例
prompt_logger = PromptLogger()
