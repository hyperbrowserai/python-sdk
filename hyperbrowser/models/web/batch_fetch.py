from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from .common import (
    PageData,
    FetchOutputOptions,
    FetchNavigationOptions,
    FetchBrowserOptions,
    FetchCacheOptions,
)
from hyperbrowser.models.consts import BatchFetchJobStatus, FetchStealthMode


class StartBatchFetchJobParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    urls: List[str]
    stealth: Optional[FetchStealthMode] = Field(
        default=None, serialization_alias="stealth"
    )
    outputs: Optional[FetchOutputOptions] = Field(
        default=None, serialization_alias="outputs"
    )
    browser: Optional[FetchBrowserOptions] = Field(
        default=None, serialization_alias="browser"
    )
    navigation: Optional[FetchNavigationOptions] = Field(
        default=None, serialization_alias="navigation"
    )
    cache: Optional[FetchCacheOptions] = Field(
        default=None, serialization_alias="cache"
    )


class GetBatchFetchJobParams(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    page: Optional[int] = Field(default=None, serialization_alias="page")
    batch_size: Optional[int] = Field(
        default=None, ge=1, serialization_alias="batchSize"
    )


class StartBatchFetchJobResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")


class BatchFetchJobStatusResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    status: BatchFetchJobStatus


class BatchFetchJobResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_alias=True,
    )

    job_id: str = Field(alias="jobId")
    status: BatchFetchJobStatus
    error: Optional[str] = None
    data: Optional[List[PageData]] = Field(default=None, alias="data")
    total_pages: int = Field(alias="totalPages")
    total_page_batches: int = Field(alias="totalPageBatches")
    current_page_batch: int = Field(alias="currentPageBatch")
    batch_size: int = Field(alias="batchSize")
