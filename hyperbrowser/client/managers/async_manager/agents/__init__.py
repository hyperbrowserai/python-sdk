from .browser_use import BrowserUseManager


class Agents:
    def __init__(self, client):
        self.browser_use = BrowserUseManager(client)
