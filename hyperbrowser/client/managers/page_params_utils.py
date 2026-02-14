from typing import Type, TypeVar

DEFAULT_PAGE_BATCH_SIZE = 100

T = TypeVar("T")


def build_page_batch_params(
    params_model: Type[T],
    *,
    page: int,
    batch_size: int = DEFAULT_PAGE_BATCH_SIZE,
) -> T:
    params_model_obj = params_model
    return params_model_obj(page=page, batch_size=batch_size)  # type: ignore[call-arg]
