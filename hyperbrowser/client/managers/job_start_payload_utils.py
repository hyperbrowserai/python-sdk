from typing import Any, Dict

from hyperbrowser.models.crawl import StartCrawlJobParams
from hyperbrowser.models.scrape import StartBatchScrapeJobParams, StartScrapeJobParams

from .serialization_utils import serialize_model_dump_to_dict


def build_scrape_start_payload(params: StartScrapeJobParams) -> Dict[str, Any]:
    return serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize scrape start params",
    )


def build_batch_scrape_start_payload(
    params: StartBatchScrapeJobParams,
) -> Dict[str, Any]:
    return serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize batch scrape start params",
    )


def build_crawl_start_payload(params: StartCrawlJobParams) -> Dict[str, Any]:
    return serialize_model_dump_to_dict(
        params,
        error_message="Failed to serialize crawl start params",
    )
