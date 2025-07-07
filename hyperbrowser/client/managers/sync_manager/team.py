from hyperbrowser.models import TeamCreditInfo


class TeamManager:
    def __init__(self, client):
        self._client = client

    def get_credit_info(self) -> TeamCreditInfo:
        response = self._client.transport.get(
            self._client._build_url("/team/credit-info")
        )
        return TeamCreditInfo(**response.data)
