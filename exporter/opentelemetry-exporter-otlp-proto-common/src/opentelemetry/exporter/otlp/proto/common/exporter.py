import gzip
import threading
import zlib
from abc import ABC, abstractmethod
from io import BytesIO
from itertools import count
from logging import getLogger
from os import environ
from time import time
from typing import (
    Callable,
    Generic,
    Iterator,
    Optional,
    Type,
    TypeVar,
)

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_TIMEOUT,
)

from opentelemetry.exporter.otlp.proto.common._internal import (
    _create_exp_backoff_with_jitter_generator,
)

logger = getLogger(__name__)
ExportResultT = TypeVar("ExportResultT")

_DEFAULT_EXPORT_TIMEOUT_S = 10


class RetryableExportError(Exception):
    def __init__(
        self, retry_delay_s: Optional[float] = None
    ):
        super().__init__()

        self.retry_delay_s = retry_delay_s


class RetryingExporter(Generic[ExportResultT]):

    def __init__(
        self,
        result_type: Type[ExportResultT],
        exporting: str,
        endpoint: str,
        timeout_s: Optional[float] = None,
    ):
        """OTLP exporter helper class.

        Encapsulates timeout behavior for shutdown and export tasks.

        Args:
            result_types: enum defining SUCCESS and FAILURE values for export.
            exporting: A string that describes the overall exporter, to be used
                in warning messages.
            endpoint: Export endpoint for use in logging.
            timeout_s: Optional timeout for exports in seconds. If None, will
                be populated from environment variable or constant.
        """
        self._result_type = result_type,
        self._exporting = exporting
        self._endpoint = endpoint
        self._timeout_s = timeout_s or float(
            environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, _DEFAULT_EXPORT_TIMEOUT_S)
        )

        self._shutdown_event = threading.Event()
        self._export_lock = threading.Lock()

    def shutdown(self, timeout_millis: float = 30_000):
        if self._shutdown_event.is_set():
            logger.warning("Exporter already shutdown, ignoring call")
            return
        locked = self._export_lock.acquire(timeout=timeout_millis * 1e-3)
        self._shutdown_event.set()
        if locked:
            self._export_lock.release()

    def export_with_retry(
        self,
        export_function: Callable[[Optional[float],], ExportResultT],
        timeout_s: float,
    ) -> ExportResultT:
        """Exports data with handling of retryable errors.

        Takes a user supplied export function of the form

            def export(timeout: Optional[float]) -> ExportResultT
                ...

        That either returns the appropriate export result, or raises a
        RetryableExportError exception if the encountered error should
        be retried.

        Retries will be attempted using exponential backoff with full jitter.
        If retry_delay_s is specified in the RetryableExportError, and that
        delay is less than the remaining timeout, then will wait at least 
        retry_delay_s seconds until next attempt.

        Will reattempt the export until timeout has passed, at which point
        the export will be abandoned and a failure will be returned.
        A pending shutdown timing out will also cause retries to time out.

        Args:
            export_function: A function handling the encoding and export step 
                without retries. Function should return an ExportResultT or
                raise RetryableExportError if a retryable error is encountered
            timeout_s: Timeout in seconds. No more reattempts will occur after
                this time.

        """
        # After the call to shutdown, subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown_event.is_set():
            logger.warning("Exporter already shutdown, ignoring batch")
            return self._result_type.FAILURE

        # Use the lowest of the possible timeouts
        timeout_s = min(timeout_s, self._timeout_s)
        deadline_s = time() + timeout_s
        # We acquire a lock to prevent shutdown from interrupting us
        try:
            if not self._export_lock.acquire(timeout=timeout_s):
                logger.warning(
                    "Exporter failed to acquire lock before timeout"
                )
                return self._result_type.FAILURE
            # _create_exp_backoff_with_jitter returns a generator that yields random delay
            # values whose upper bounds grow exponentially. The upper bound will cap at max
            # value (never wait more than 64 seconds at once)
            max_value = 64
            for delay_s in _create_exp_backoff_with_jitter_generator(
                max_value=max_value
            ):
                remaining_time_s = deadline_s - time()

                if remaining_time_s < 1e-09:
                    logger.warning(
                        "Timed out exporting %s to %s",
                        self._exporting,
                        self._endpoint,
                    )
                    return self._result_type.FAILURE

                if self._shutdown_event.is_set():
                    logger.warning(
                        "Shutdown encountered while exporting %s to %s",
                        self._exporting,
                        self._endpoint,
                    )
                    return self._result_type.FAILURE

                try:
                    return export_function(
                        timeout_millis=remaining_time_s,
                    )
                except RetryableExportError as err:
                    time_remaining_s = deadline_s - time()
                    delay_s = min(time_remaining_s, delay_s)
                    if err.retry_delay_s is not None:
                        if err.retry_delay_s > time_remaining_s:
                            # We should not retry before the requested interval, so
                            # we must fail out prematurely
                            return self._result_type.FAILURE
                        delay_s = max(err.retry_delay_s, delay_s)
                    logger.warning(
                        "%s, retrying in %ss.",
                        err.log_warning_message,
                        delay_s,
                    )
                    self._shutdown_event.wait(delay_s)
        finally:
            self._export_lock.release()

        return self._result_type.FAILURE


def _create_exp_backoff_generator(max_value: int = 0) -> Iterator[int]:
    """
    Generates an infinite sequence of exponential backoff values. The sequence starts
    from 1 (2^0) and doubles each time (2^1, 2^2, 2^3, ...). If a max_value is specified
    and non-zero, the generated values will not exceed this maximum, capping at max_value
    instead of growing indefinitely.

    Parameters:
    - max_value (int, optional): The maximum value to yield. If 0 or not provided, the
      sequence grows without bound.

    Returns:
    Iterator[int]: An iterator that yields the exponential backoff values, either uncapped or
    capped at max_value.

    Example:
    ```
    gen = _create_exp_backoff_generator(max_value=10)
    for _ in range(5):
        print(next(gen))
    ```
    This will print:
    1
    2
    4
    8
    10

    Note: this functionality used to be handled by the 'backoff' package.
    """
    for i in count(0):
        out = 2**i
        yield min(out, max_value) if max_value else out


def _create_exp_backoff_with_jitter_generator(
    max_value: int = 0,
) -> Iterator[float]:
    """
    Generates an infinite sequence of exponential backoff values with jitter using the
    FullJitter approach. For each element "n" in the exponential backoff series created
    by _create_exp_backoff(max_value), yields a random number in the half-open range [0,n).

    This algorithm is originally documented at
    https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

    Parameters:
    - max_value (int, optional): The maximum value to yield. If 0 or not provided, the
      sequence grows without bound.

    Returns:
    Iterator[int]: An iterator that yields the exponential backoff values, either uncapped or
    capped at max_value.

    Example:
    ```
    import random
    random.seed(20240220)
    gen = _create_exp_backoff_with_jitter_generator(max_value=10)
    for _ in range(5):
        print(next(gen))
    ```
    This will print:
        0.1341603010697452
        0.34773275270578097
        3.6022913287022913
        6.663388602254524
        10

    """
    for i in _create_exp_backoff_generator(max_value):
        yield uniform(0, i)
