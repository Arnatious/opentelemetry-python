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

import threading
import time
from logging import WARNING
from typing import Any, Iterable, Optional, Sequence
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.exporter.otlp.proto.common._internal import (
    InvalidCompressionValueException,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.exporter import (
    _DEFAULT_EXPORT_TIMEOUT_S,
    ExportServiceRequestT,
    OTLPExporterMixin,
    SDKDataT,
    StatusCode,
    environ_to_compression,
)
from opentelemetry.sdk.environment_variables import OTEL_EXPORTER_OTLP_TIMEOUT

result_mock = Mock()


class TestOTLPExporterMixin(TestCase):
    def assert_export_failure(
        self, exporter: OTLPExporterMixin, *args, **kwargs
    ):
        # pylint: disable=protected-access
        self.assertIs(
            exporter._export([], *args, *kwargs), result_mock.FAILURE
        )

    def assert_export_success(
        self, exporter: OTLPExporterMixin, *args, **kwargs
    ):
        # pylint: disable=protected-access
        self.assertIs(
            exporter._export([], *args, *kwargs), result_mock.SUCCESS
        )

    def test_environ_to_compression(self):
        with patch.dict(
            "os.environ",
            {
                "test_gzip": "gzip",
                "test_gzip_caseinsensitive_with_whitespace": " GzIp ",
                "test_invalid": "some invalid compression",
            },
        ):
            self.assertEqual(
                environ_to_compression("test_gzip"), Compression.Gzip
            )
            self.assertEqual(
                environ_to_compression(
                    "test_gzip_caseinsensitive_with_whitespace"
                ),
                Compression.Gzip,
            )
            self.assertIsNone(
                environ_to_compression("missing_key"),
            )
            with self.assertRaises(InvalidCompressionValueException):
                environ_to_compression("test_invalid")
