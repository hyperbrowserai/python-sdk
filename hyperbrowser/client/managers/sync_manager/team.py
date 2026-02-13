from hyperbrowser.models import TeamCreditInfo
from ..response_utils import parse_response_model


class TeamManager:
    def __init__(self, client):
        self._client = client

    def get_credit_info(self) -> TeamCreditInfo:
        response = self._client.transport.get(
            self._client._build_url("/team/credit-info")
        )
        return parse_response_model(
            response.data,
            model=TeamCreditInfo,
            operation_name="team credit info",
        )
