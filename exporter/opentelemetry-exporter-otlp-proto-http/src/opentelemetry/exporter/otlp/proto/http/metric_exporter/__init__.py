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

from os import environ
from typing import Dict, Optional, Any, Callable, List

from deprecated import deprecated

from opentelemetry.exporter.otlp.proto.common._internal import (
    _get_resource_data,
)
from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    OTLPMetricExporterMixin,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.exporter import OTLPExporterMixin, environ_to_compression
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (  # noqa: F401
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    AnyValue,
    ArrayValue,
    KeyValue,
    KeyValueList,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    InstrumentationScope,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource  # noqa: F401
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2  # noqa: F401
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
    OTEL_EXPORTER_OTLP_METRICS_COMPRESSION,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.metrics.export import (  # noqa: F401
    Gauge,
    Histogram as HistogramType,
    Sum,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.util.re import parse_env_headers

import requests
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_METRICS_EXPORT_PATH = "v1/metrics"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPMetricExporter(
    MetricExporter,
    OTLPMetricExporterMixin,
    OTLPExporterMixin[MetricsData, MetricExporter, MetricExportResult],
):

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
        preferred_temporality: Dict[type, AggregationTemporality] = None,
        preferred_aggregation: Dict[type, Aggregation] = None,
    ):
        environ_endpoint = self._append_telemetry_signal_path(
            environ.get(OTEL_EXPORTER_OTLP_METRICS_ENDPOINT, DEFAULT_ENDPOINT)
        )
        if headers is None:
            environ_headers = environ.get(OTEL_EXPORTER_OTLP_METRICS_HEADERS)
            if environ_headers is not None:
                headers = parse_env_headers(environ_headers)
        if timeout is None:
            environ_timeout = environ.get(OTEL_EXPORTER_OTLP_METRICS_TIMEOUT)
            if environ_timeout is not None:
                timeout = float(environ_timeout)
        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION)
            if compression is None
            else compression
        )
        headers.update(
            {"Content-Type": "application/x-protobuf"}
        )
        
        self._common_configuration(
            preferred_temporality, preferred_aggregation
        )

        OTLPExporterMixin.__init__(
            self,
            endpoint=endpoint or environ_endpoint,
            certificate_file=certificate_file
            or environ.get(OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE),
            headers=headers,
            timeout=timeout,
            compression=compression,
            session=session,
        )

    @staticmethod
    def _retryable(resp: requests.Response) -> bool:
        if resp.status_code == 408:
            return True
        if resp.status_code >= 500 and resp.status_code <= 599:
            return True
        return False

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        serialized_data = encode_metrics(metrics_data).SerializeToString
        return self._export(serialized_data=serialized_data, timeout_millis=timeout_millis)
    
    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass

    @property
    def _result(self):
        return MetricExportResult

    @property
    def _exporting(self) -> str:
        return "metrics"

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
        
    def _append_telemetry_signal_path(endpoint: str) -> str:
        if endpoint.endswith("/"):
            return endpoint + DEFAULT_METRICS_EXPORT_PATH
        return endpoint + f"/{DEFAULT_METRICS_EXPORT_PATH}"


@deprecated(
    version="1.18.0",
    reason="Use one of the encoders from opentelemetry-exporter-otlp-proto-common instead",
)
def get_resource_data(
    sdk_resource_scope_data: Dict[SDKResource, Any],  # ResourceDataT?
    resource_class: Callable[..., PB2Resource],
    name: str,
) -> List[PB2Resource]:
    return _get_resource_data(sdk_resource_scope_data, resource_class, name)
