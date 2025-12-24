# werewolf_game/agents/user_agent.py

import asyncio
from agentscope.agent import UserAgent
from agentscope.message import Msg
import sys


class MyUserAgent(UserAgent):
    """A custom UserAgent that prints private messages and prompts."""

    async def reply(self, x: Msg) -> Msg:
        """
        Override the reply method to first print the content of the input
        message and then wait for user input asynchronously.
        """
        # Print the prompt message from the game master
        print(f"\n{x.content}")
        sys.stdout.flush()
        
        # Get user input asynchronously to avoid blocking the event loop
        user_input = await asyncio.to_thread(input, "User Input: ")
        
        # Echo the input back to the console, which is a common UX pattern
        print(f"{self.name}: {user_input}")
        
        # Return the input wrapped in a Msg object
        return Msg(self.name, user_input, role="user")

    async def observe(self, x: Msg) -> None:
        """
        Override the observe method to print private system messages
        to the console for the user.
        """
        # Check for the private message prefix in the content
        if x.role == "system" and x.content.startswith("__PRIVATE__"):
            # Strip the prefix before printing to the user
            private_content = x.content.replace("__PRIVATE__", "", 1)
            print(f"\n[私密提示]: {private_content}")
            sys.stdout.flush()
        
        # Don't call the original observe, as it might print public messages
        # that we are already printing through the public channel announcements.
        # If you need other observe functionalities, you can add them here.
        pass

def create_user_agent() -> MyUserAgent:
    """
    Creates a custom user agent instance.
    """
    return MyUserAgent(name="User_Player")
