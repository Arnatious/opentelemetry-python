import gzip
import threading
import zlib
from abc import ABC, abstractmethod
from io import BytesIO
from logging import getLogger
from os import environ
from time import time
from typing import (
    Dict,
    Generic,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)

from opentelemetry.exporter.otlp.proto.common._internal import (
    _create_exp_backoff_with_jitter_generator,
)

logger = getLogger(__name__)
SDKDataT = TypeVar("SDKDataT")
ExportServiceRequestT = TypeVar("ExportServiceRequestT")
TypingResourceT = TypeVar("TypingResourceT")
ExportResultT = TypeVar("ExportResultT")

_DEFAULT_EXPORT_TIMEOUT_S = 10


class OTLPExportError(Exception):
    def __init__(self, log_warning_message: str) -> None:
        super().__init__()
        self.log_warning_message = log_warning_message


class NonRetryableExportError(OTLPExportError):
    def __init__(self, log_warning_message: str, result: ExportResultT):
        super().__init__(log_warning_message)
        self.result = result


class RetryableExportError(OTLPExportError):
    def __init__(
        self, log_warning_message: str, retry_delay_s: Optional[float] = None
    ):
        super().__init__(log_warning_message)

        self.retry_delay_s = retry_delay_s


class OTLPExporterMixin(ABC, Generic[SDKDataT, ExportResultT]):
    """OTLP exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        timeout: Backend request timeout in seconds
        compression: compression method to use
    """

    def __init__(
        self,
        *args,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> None:
        self._timeout = timeout or float(
            environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, _DEFAULT_EXPORT_TIMEOUT_S)
        )

        self._shutdown_event = threading.Event()
        self._export_lock = threading.Lock()

        super().__init__(*args, **kwargs)

    @abstractmethod
    def _shutdown(self):
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs):
        if self._shutdown.is_set():
            logger.warning("Exporter already shutdown, ignoring call")
            return
        locked = self._export_lock.acquire(timeout=timeout_millis / 1e3)
        self._shutdown()
        self._shutdown.set()
        if locked:
            self._export_lock.release()

    @abstractmethod
    def _export(
        self,
        data: SDKDataT,
        *args,
        timeout_millis: float = _DEFAULT_EXPORT_TIMEOUT_S * 1e3,
        **kwargs,
    ) -> bool:
        pass

    def _export_with_retry(
        self,
        data: SDKDataT,
        *args,
        timeout_millis: float = _DEFAULT_EXPORT_TIMEOUT_S * 1e3,
        **kwargs,
    ) -> ExportResultT:
        # After the call to shutdown, subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown_event.is_set():
            logger.warning("Exporter already shutdown, ignoring batch")
            return self._result.FAILURE

        # Use the lowest of the possible timeouts
        timeout_s = min((timeout_millis / 1e3), self._timeout)
        deadline_s = time() + timeout_s
        # We acquire a lock to prevent shutdown from interrupting us
        try:
            if not self._export_lock.acquire(timeout=timeout_s):
                logger.warning(
                    "Exporter failed to acquire lock before timeout"
                )
                return self._result.FAILURE
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
                    return self._result.FAILURE

                if self._shutdown_event.is_set():
                    logger.warning(
                        "Shutdown encountered while exporting %s to %s",
                        self._exporting,
                        self._endpoint,
                    )
                    return self._result.FAILURE

                try:
                    self._export(
                        data, *args, timeout_millis=remaining_time_s, **kwargs
                    )
                    return self._result.SUCCESS
                except NonRetryableExportError as err:
                    return err.result
                except RetryableExportError as err:
                    time_remaining_s = deadline_s - time()
                    delay_s = min(time_remaining_s, delay_s)
                    if err.retry_delay_s is not None:
                        delay_s = min(err.retry_delay_s, time_remaining_s)
                    logger.warning(
                        "%s, retrying in %ss.",
                        err.log_warning_message,
                        delay_s,
                    )
                    self._shutdown_event.wait(delay_s)
        finally:
            self._export_lock.release()

        return self._result.FAILURE

    @abstractmethod
    def _retryable(self, error):
        pass

    @property
    @abstractmethod
    def _exporting(self) -> str:
        """
        Returns a string that describes the overall exporter, to be used in
        warning messages.
        """
        pass

    @property
    @abstractmethod
    def _result(self) -> ExportResultT:
        """
        Enum defining export result states to be used.
        """
        pass
