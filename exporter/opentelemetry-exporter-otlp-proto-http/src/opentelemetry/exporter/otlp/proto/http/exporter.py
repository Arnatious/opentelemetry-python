# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OTLP GRPC Proto HTTP Exporter"""

import gzip
import threading
import zlib
from abc import ABC, abstractmethod
from io import BytesIO
from logging import getLogger
from os import environ
from typing import (
    Dict,
    Generic,
    Optional,
    TypeVar,
    Union,
)

from opentelemetry.exporter.otlp.proto.common.exporter import (
    RetryableExportError,
)
from opentelemetry.exporter.otlp.proto.common._internal import (
    InvalidCompressionValueException,
)
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

import requests

logger = getLogger(__name__)
SDKDataT = TypeVar("SDKDataT")
ResourceDataT = TypeVar("ResourceDataT")
ExportServiceRequestT = TypeVar("ExportServiceRequestT")
ExportResultT = TypeVar("ExportResultT")


class OTLPExporterMixin(
    Generic[SDKDataT, ExportServiceRequestT, ExportResultT], ABC
):
    """OTLP HTTP exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        certificate_file: Name of file containing certificate for server authentication
        headers: Headers to send when exporting
        timeout: Backend request timeout in seconds
        compression: compression method to use
        session: Requests session to use
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(timeout=timeout, **kwargs)

        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_ENDPOINT, "http://localhost:4318"
        )
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_CERTIFICATE, True
        )

        self._headers = headers or parse_env_headers(
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, "")
        )
        self._compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_COMPRESSION)
            if compression is None
            else compression
        ) or Compression.NoCompression

        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )

    def _export(
        self,
        data: SDKDataT,
        timeout_millis: float,
        *args,
        **kwargs,
    ) -> ExportResultT:
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = zlib.compress(bytes(data))

        resp = self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=timeout_millis,
        )

        if resp.ok:
            return self._result.SUCCESS
        elif _status_code_retryable(resp):
            raise RetryableExportError(
                f"Transient error {resp.reason} encountered while exporting {self._exporting} batch",
                resp.reason,
                self._exporting,
            )
        else:
            logger.error(
                "Failed to export batch code: %s, reason: %s",
                resp.status_code,
                resp.text,
            )
            return self._result.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs):
        if self._shutdown.is_set():
            logger.warning("Exporter already shutdown, ignoring call")
            return
        locked = self._export_lock.acquire(timeout=timeout_millis / 1e3)
        self._session.close()
        self._shutdown.set()
        if locked:
            self._export_lock.release()

    @abstractmethod
    def _append_telemetry_signal_path(self, endpoint: str) -> str:
        pass


def _status_code_retryable(resp: requests.Response) -> bool:
    if resp.status_code == 408:
        return True
    if resp.status_code >= 500 and resp.status_code <= 599:
        return True
    return False


def environ_to_compression(environ_key: str) -> Optional[Compression]:
    environ_value = (
        environ[environ_key].lower().strip()
        if environ_key in environ
        else None
    )
    try:
        return Compression(environ_value)
    except ValueError:
        raise InvalidCompressionValueException(environ_key, environ_value)
