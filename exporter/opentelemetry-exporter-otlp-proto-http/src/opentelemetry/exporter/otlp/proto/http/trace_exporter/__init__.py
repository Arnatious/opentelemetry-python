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

from os import environ
from typing import Dict, Optional, Sequence

import requests

from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.http.exporter import (
    OTLPExporterMixin,
    environ_to_compression,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.exporter.otlp.proto.http import (
    Compression,
)
from opentelemetry.util.re import parse_env_headers


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TRACES_EXPORT_PATH = "v1/traces"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPSpanExporter(
    SpanExporter,
    OTLPExporterMixin[ReadableSpan, SpanExportResult, SpanExportResult],
):

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
    ):
        environ_endpoint = self._append_telemetry_signal_path(
            environ.get(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, DEFAULT_ENDPOINT)
        )
        if headers is None:
            environ_headers = environ.get(OTEL_EXPORTER_OTLP_TRACES_HEADERS)
            if environ_headers is not None:
                headers = parse_env_headers(environ_headers)
        if timeout is None:
            environ_timeout = environ.get(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT)
            if environ_timeout is not None:
                timeout = float(environ_timeout)
        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION)
            if compression is None
            else compression
        )

        super().__init__(
            endpoint=endpoint or environ_endpoint,
            certificate_file=certificate_file
            or environ.get(OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE),
            headers=headers,
            timeout=timeout,
            compression=compression,
            session=session,
        )

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True

    def export(
        self,
        data: Sequence[ReadableSpan],
        timeout_millis: int = 10_000,
        **kwargs,
    ) -> SpanExportResult:
        return self._export(
            encode_spans(data).SerializeToString(),
            timeout_millis=timeout_millis,
        )

    @property
    def _result(self):
        return SpanExportResult

    @property
    def _exporting(self) -> str:
        return "span"

    def _append_telemetry_signal_path(self, endpoint: str) -> str:
        if endpoint.endswith("/"):
            return endpoint + DEFAULT_TRACES_EXPORT_PATH
        return endpoint + f"/{DEFAULT_TRACES_EXPORT_PATH}"
