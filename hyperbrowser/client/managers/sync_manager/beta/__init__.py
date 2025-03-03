from .agents import Agents


class Beta:
    def __init__(self, client):
        self.agents = Agents(client)
