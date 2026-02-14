from hyperbrowser.models import TeamCreditInfo
from ..team_operation_metadata import TEAM_OPERATION_METADATA
from ..team_request_utils import get_team_resource_async
from ..team_route_constants import TEAM_CREDIT_INFO_ROUTE_PATH


class TeamManager:
    _OPERATION_METADATA = TEAM_OPERATION_METADATA
    _CREDIT_INFO_ROUTE_PATH = TEAM_CREDIT_INFO_ROUTE_PATH

    def __init__(self, client):
        self._client = client

    async def get_credit_info(self) -> TeamCreditInfo:
        return await get_team_resource_async(
            client=self._client,
            route_path=self._CREDIT_INFO_ROUTE_PATH,
            model=TeamCreditInfo,
            operation_name=self._OPERATION_METADATA.get_credit_info_operation_name,
        )
