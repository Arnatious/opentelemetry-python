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
from types import MethodType
from typing import Any, Iterable, Optional, Sequence
from unittest import TestCase
from unittest.mock import Mock, patch

from google.protobuf.duration_pb2 import Duration
from google.rpc.error_details_pb2 import RetryInfo
from grpc import Compression

from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    _DEFAULT_EXPORT_TIMEOUT_S,
    ExportServiceRequestT,
    InvalidCompressionValueException,
    OTLPExporterMixin,
    RpcError,
    SDKDataT,
    StatusCode,
    environ_to_compression,
)
from opentelemetry.sdk.environment_variables import OTEL_EXPORTER_OTLP_TIMEOUT


result_mock = Mock()


def mock_exporter_factory(
    export_side_effect: Any = None, *args, **kwargs
) -> OTLPExporterMixin:
    """Create an instance of a class inheriting from OTLPExporterMixin.

    The return value's _result class attribute will be set to result_mock.

    Parameters:
    - export_side_effect (Any, optional): Side effect of the _stub.Export() Mock. See
      `unittest.mock.Mock`'s side_effect parameter for more details.
    - *args: Positional arguments passed to the OTLPExporterMixin constructor
    - **kwargs: Keyword arguments passed to the OTLPExporterMixin

    Returns:
    OTLPExporterMixin: An object of a new class inheriting from OTLPExporterMixin.
    """

    class OTLPMockExporter(OTLPExporterMixin):
        _result = result_mock
        _stub = Mock(
            return_value=Mock(**{"Export.side_effect": export_side_effect})
        )

        def _translate_data(
            self, data: Sequence[SDKDataT]
        ) -> ExportServiceRequestT:
            pass

        @property
        def _exporting(self) -> str:
            return "mock"

    return OTLPMockExporter(*args, **kwargs)


def rpc_error_factory(
    code: Any = None,
    trailing_metadata: Optional[Iterable] = None,
):
    """Create an RpcError with the specified code and trailing metadata.

    Wraps the parameters as methods that will always return the argument values.

    Paramters:
    - code (Any, optional): The value to be returned when calling return_value.code.
    - trailing_metadata (Any, optional): The value to be returned when calling return_value.trailing_metadata

    Returns:
    RpcError: The specified RpcError.
    """
    rpc_error = RpcError()

    if trailing_metadata is None:
        trailing_metadata = {}

    rpc_error.code = MethodType(lambda self: code, rpc_error)
    rpc_error.trailing_metadata = MethodType(
        lambda self: trailing_metadata, rpc_error
    )
    return rpc_error


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

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_with_jitter_generator",
        return_value=[0],
    )
    def test_export_warning(self, mock_expo):

        otlp_mock_exporter = mock_exporter_factory(
            export_side_effect=rpc_error_factory()
        )

        with self.assertLogs(level=WARNING) as warning:
            # pylint: disable=protected-access
            self.assert_export_failure(otlp_mock_exporter)
            self.assertEqual(
                warning.records[0].message,
                "Failed to export mock to localhost:4317, error code: None",
            )

        otlp_mock_exporter = mock_exporter_factory(
            export_side_effect=rpc_error_factory(code=StatusCode.CANCELLED)
        )

        with self.assertLogs(level=WARNING) as warning:
            # pylint: disable=protected-access
            self.assert_export_failure(otlp_mock_exporter)
            self.assertEqual(
                warning.records[0].message,
                (
                    "Transient error StatusCode.CANCELLED encountered "
                    "while exporting mock to localhost:4317, retrying in 0s."
                ),
            )

    def test_export_retry(self):
        """
        Test we retry until successfully exporting.
        """

        rpc_error = rpc_error_factory(code=StatusCode.UNAVAILABLE)

        otlp_mock_exporter = mock_exporter_factory(
            export_side_effect=[rpc_error, rpc_error, None],
        )
        try:
            self.assert_export_success(otlp_mock_exporter)
        except StopIteration:
            raise AssertionError("Export was retried after success") from None

    def test_export_timeout_retry_delay(self):
        """
        Test we retry using the delay specified in the RPC error.
        """

        retry_delay_s = 2

        rpc_error = rpc_error_factory(
            code=StatusCode.UNAVAILABLE,
            trailing_metadata={
                "google.rpc.retryinfo-bin": RetryInfo(
                    retry_delay=Duration(seconds=retry_delay_s)
                ).SerializeToString()
            },
        )

        export_results = [rpc_error, rpc_error]
        export_iterator = iter(export_results)
        retry_times = []

        # Export will raise each rpc_error in export_results, then
        # return indicating success
        def export(*args, **kwargs):
            nonlocal retry_times
            retry_times.append(time.time())
            try:
                raise next(export_iterator)
            except StopIteration:
                return

        otlp_mock_exporter = mock_exporter_factory(
            export_side_effect=export,
        )
        self.assert_export_success(otlp_mock_exporter)

        real_delays_between_exports = [
            b - a for a, b in zip(retry_times, retry_times[1:])
        ]
        # There should have been len(export_results) reattempts
        self.assertEqual(len(real_delays_between_exports), len(export_results))

        for delay in real_delays_between_exports:
            # Each reattempt should have been retry_delay_s aften the previous attempt
            self.assertGreaterEqual(delay, retry_delay_s)

    def check_timeout(self, exporter: OTLPExporterMixin, timeout: float):
        start_time = time.time()
        self.assert_export_failure(exporter)
        end_time = time.time()
        # We can be slightly over the timeout because of sleep()
        self.assertLessEqual(end_time - start_time, timeout + 1)

    def check_timeout_from_arg(
        self, exporter: OTLPExporterMixin, timeout: float
    ):
        start_time = time.time()
        self.assert_export_failure(exporter, timeout=timeout)
        end_time = time.time()
        # We can be slightly over the timeout because of sleep()
        self.assertLessEqual(end_time - start_time, timeout + 1)

    def test_export_timeout(self):
        rpc_error = rpc_error_factory(StatusCode.UNAVAILABLE)

        with self.subTest("default timeout"):
            otlp_mock_exporter = mock_exporter_factory(
                export_side_effect=rpc_error,
            )
            self.check_timeout(otlp_mock_exporter, _DEFAULT_EXPORT_TIMEOUT_S)

        with self.subTest("timeout from environment variable"):
            timeout = _DEFAULT_EXPORT_TIMEOUT_S / 2
            with patch.dict(
                "os.environ", **{OTEL_EXPORTER_OTLP_TIMEOUT: str(timeout)}
            ):
                otlp_mock_exporter = mock_exporter_factory(
                    export_side_effect=rpc_error,
                )
                self.check_timeout(otlp_mock_exporter, timeout)

        with self.subTest("timeout from constructor"):
            timeout = _DEFAULT_EXPORT_TIMEOUT_S / 2
            otlp_mock_exporter = mock_exporter_factory(
                export_side_effect=rpc_error, timeout=timeout
            )
            self.check_timeout(otlp_mock_exporter, timeout)

    def test_export_timeout_retry_delay_timeout(self):
        """
        Test that a retry_delay greater than the remaining timeout fails.
        """

        retry_delay = 10

        rpc_error = rpc_error_factory(
            StatusCode.UNAVAILABLE,
            {
                "google.rpc.retryinfo-bin": RetryInfo(
                    retry_delay=Duration(seconds=retry_delay)
                ).SerializeToString()
            },
        )

        # We need a sleep for the thread to yield properly, or else it will hog
        # the lock.
        def fake_export(*args, **kwargs):
            time.sleep(0)
            raise rpc_error

        otlp_mock_exporter = mock_exporter_factory(
            export_side_effect=fake_export,
            timeout=retry_delay / 2,
        )
        self.assertIs(
            # pylint: disable=protected-access
            otlp_mock_exporter._export(data={}),
            result_mock.FAILURE,
        )

    def test_shutdown(self):
        otlp_mock_exporter = mock_exporter_factory()

        # pylint: disable=protected-access
        self.assert_export_success(otlp_mock_exporter)
        otlp_mock_exporter.shutdown()
        with self.assertLogs(level=WARNING) as warning:
            # pylint: disable=protected-access
            self.assert_export_failure(otlp_mock_exporter)
            self.assertEqual(
                warning.records[0].message,
                "Exporter already shutdown, ignoring batch",
            )

    def test_shutdown_wait_last_export_success(self):
        rpc_error = rpc_error_factory(StatusCode.UNAVAILABLE)

        export_iterator = iter([rpc_error, rpc_error])
        # We use two events to protect against flakyness from threading by
        # forcing execution order
        is_exporting = threading.Event()
        test_ready_to_continue = threading.Event()

        # Export will raise each rpc_error in export_results, then return
        # to indicate success. Essentially the same as a mock side effect of
        # [rpc_error, rpc_error, None].
        # We need a sleep(0) to yield the thread appropriately or else export
        # could complete before shutdown is run.
        def fake_export(*args, **kwargs):
            if not is_exporting.is_set():
                is_exporting.set()
                test_ready_to_continue.wait()
            time.sleep(0)
            try:
                raise next(export_iterator)
            except StopIteration:
                return

        otlp_mock_exporter = mock_exporter_factory(
            export_side_effect=fake_export
        )

        result = None

        def capture_export_result():
            nonlocal result
            # pylint: disable=protected-access
            result = otlp_mock_exporter._export([])

        export_thread = threading.Thread(target=capture_export_result)
        export_thread.start()
        try:
            # Ensure that lock has been acquired and an export is being attempted
            is_exporting.wait()
            start_time = time.time()
            shutdown_thread = threading.Thread(
                target=otlp_mock_exporter.shutdown
            )
            shutdown_thread.start()
            test_ready_to_continue.set()
            shutdown_thread.join()
            self.assertLessEqual(
                time.time() - start_time, _DEFAULT_EXPORT_TIMEOUT_S
            )
            # pylint: disable=protected-access
            self.assertTrue(otlp_mock_exporter._shutdown.is_set())
            # pylint: disable=protected-access
            self.assertFalse(otlp_mock_exporter._export_lock.locked())
        finally:
            export_thread.join()
            shutdown_thread.join()
        self.assertIs(result, result_mock.SUCCESS)

    def test_shutdown_timeout_cancels_export_retries(self):
        """
        Test that shutdown timing out will cancel any ongoing retries.
        """

        rpc_error = rpc_error_factory(StatusCode.UNAVAILABLE)
        # We use two events to protect against flakyness from threading by
        # forcing execution order
        is_exporting = threading.Event()
        test_ready_to_continue = threading.Event()

        # We need a sleep(0) to yield the thread appropriately or else export
        # could complete before shutdown is run.
        def fake_export(*args, **kwargs):
            if not is_exporting.is_set():
                is_exporting.set()
                test_ready_to_continue.wait()
            time.sleep(0)
            raise rpc_error

        otlp_mock_exporter = mock_exporter_factory(
            export_side_effect=fake_export
        )

        result = None

        def capture_export_result():
            nonlocal result
            # pylint: disable=protected-access
            result = otlp_mock_exporter._export([])

        export_thread = threading.Thread(target=capture_export_result)
        with self.assertLogs(level=WARNING) as warning:
            export_thread.start()
            try:
                # Ensure that lock has been acquired and an export is being attempted
                is_exporting.wait()
                start_time = time.time()
                shutdown_thread = threading.Thread(
                    target=otlp_mock_exporter.shutdown,
                    kwargs={"timeout_millis": 10},
                )
                shutdown_thread.start()
                test_ready_to_continue.set()
                shutdown_thread.join()
                export_thread.join()
                self.assertLessEqual(
                    time.time() - start_time, _DEFAULT_EXPORT_TIMEOUT_S
                )
                # pylint: disable=protected-access
                self.assertTrue(otlp_mock_exporter._shutdown.is_set())
                # pylint: disable=protected-access
                self.assertFalse(otlp_mock_exporter._export_lock.locked())
            finally:
                export_thread.join()
                shutdown_thread.join()

        self.assertIs(result, result_mock.FAILURE)
        self.assertEqual(
            warning.records[-1].message,
            "Shutdown encountered while exporting mock to localhost:4317",
        )
