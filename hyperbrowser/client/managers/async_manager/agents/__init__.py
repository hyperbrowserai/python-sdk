class Agents:
    def __init__(self, client):
        from .browser_use import BrowserUseManager

        self.browser_use = BrowserUseManager(client)
