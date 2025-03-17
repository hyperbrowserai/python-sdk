from .browser_use import BrowserUseManager
from .cua import CuaManager


class Agents:
    def __init__(self, client):
        self.browser_use = BrowserUseManager(client)
        self.cua = CuaManager(client)
