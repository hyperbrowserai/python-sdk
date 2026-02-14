from typing import Any, Dict, Optional

from hyperbrowser.models.crawl import GetCrawlJobParams
from hyperbrowser.models.scrape import GetBatchScrapeJobParams

from .serialization_utils import serialize_model_dump_or_default


def build_batch_scrape_get_params(
    params: Optional[GetBatchScrapeJobParams] = None,
) -> Dict[str, Any]:
    return serialize_model_dump_or_default(
        params,
        default_factory=GetBatchScrapeJobParams,
        error_message="Failed to serialize batch scrape get params",
    )


def build_crawl_get_params(
    params: Optional[GetCrawlJobParams] = None,
) -> Dict[str, Any]:
    return serialize_model_dump_or_default(
        params,
        default_factory=GetCrawlJobParams,
        error_message="Failed to serialize crawl get params",
    )
