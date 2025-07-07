from pydantic import BaseModel, ConfigDict, Field


class TeamCreditInfo(BaseModel):
    """
    Represents a team's credit information.
    """

    model_config = ConfigDict(
        populate_by_alias=True,
    )

    usage: int = Field(alias="usage")
    limit: int = Field(alias="limit")
    remaining: int = Field(alias="remaining")
