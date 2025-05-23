from .browser_use import BrowserUseManager
from .cua import CuaManager
from .claude_computer_use import ClaudeComputerUseManager
from .hyper_agent import HyperAgentManager


class Agents:
    def __init__(self, client):
        self.browser_use = BrowserUseManager(client)
        self.cua = CuaManager(client)
        self.claude_computer_use = ClaudeComputerUseManager(client)
        self.hyper_agent = HyperAgentManager(client)
