# Copyright The OpenTelemetry Authors
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

"""OTLP Span Exporter"""

import logging
from os import environ
from typing import Dict, Optional, Sequence, Tuple, Union
from typing import Sequence as TypingSequence


from grpc import ChannelCredentials, Compression

from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    OTLPExporterMixin,
    _get_credentials,
    environ_to_compression,
)
from opentelemetry.exporter.otlp.proto.grpc.exporter import (  # noqa: F401
    get_resource_data,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    InstrumentationScope,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (  # noqa: F401
    ScopeSpans,
    ResourceSpans,
    Span as CollectorSpan,
)
from opentelemetry.proto.trace.v1.trace_pb2 import Status  # noqa: F401
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_INSECURE,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class OTLPSpanExporter(
    SpanExporter,
    OTLPExporterMixin[
        ReadableSpan, ExportTraceServiceRequest, SpanExportResult
    ],
):
    # pylint: disable=unsubscriptable-object
    """OTLP span exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: Connection type
        credentials: Credentials object for server authentication
        headers: Headers to send when exporting
        timeout: Backend request timeout in seconds
        compression: gRPC compression method to use
    """

    _result = SpanExportResult
    _stub = TraceServiceStub

    def __init__(
        self,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[
            Union[TypingSequence[Tuple[str, str]], Dict[str, str], str]
        ] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):

        if insecure is None:
            insecure = environ.get(OTEL_EXPORTER_OTLP_TRACES_INSECURE)
            if insecure is not None:
                insecure = insecure.lower() == "true"

        if (
            not insecure
            and environ.get(OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE) is not None
        ):
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE
            )

        environ_timeout = environ.get(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT)
        environ_timeout = (
            int(environ_timeout) if environ_timeout is not None else None
        )

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION)
            if compression is None
            else compression
        )

        super().__init__(
            **{
                "endpoint": endpoint
                or environ.get(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT),
                "insecure": insecure,
                "credentials": credentials,
                "headers": headers
                or environ.get(OTEL_EXPORTER_OTLP_TRACES_HEADERS),
                "timeout": timeout or environ_timeout,
                "compression": compression,
            }
        )

    def _translate_data(
        self, data: Sequence[ReadableSpan]
    ) -> ExportTraceServiceRequest:
        return encode_spans(data)

    def export(
        self,
        spans: Sequence[ReadableSpan],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> SpanExportResult:
        return self._export(spans, timeout_millis=timeout_millis)

    def shutdown(self) -> None:
        OTLPExporterMixin.shutdown(self)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True

    @property
    def _exporting(self):
        return "traces"
