import time
import unittest
from itertools import repeat
from logging import WARNING
from unittest.mock import Mock, patch, ANY

from opentelemetry.exporter.otlp.proto.common.exporter import (
    _ExportProtocol,
    RetryableExportError,
    RetryingExporter,
    _DEFAULT_EXPORT_TIMEOUT_S,
    logger as exporter_logger,
)

result_type = Mock()


class TestRetryableExporter(unittest.TestCase):
    def test_export_no_retry(self):
        export_func = Mock()
        exporter = RetryingExporter(export_func, result_type)
        with self.subTest("Export success"):
            export_func.reset_mock()
            export_func.configure_mock(return_value=result_type.SUCCESS)
            pos_arg = Mock()
            with self.assertRaises(AssertionError):
                with self.assertLogs(level=WARNING):
                    result = exporter.export_with_retry(
                        _DEFAULT_EXPORT_TIMEOUT_S, pos_arg, foo="bar"
                    )
            self.assertIs(result, result_type.SUCCESS)
            export_func.assert_called_once_with(ANY, pos_arg, foo="bar")

        with self.subTest("Export Fail"):
            export_func.reset_mock()
            export_func.configure_mock(return_value=result_type.FAILURE)
            pos_arg = Mock()
            with self.assertNoLogs(exporter_logger, level=WARNING):
                result = exporter.export_with_retry(
                    _DEFAULT_EXPORT_TIMEOUT_S, pos_arg, foo="bar"
                )
            self.assertIs(result, result_type.FAILURE)
            export_func.assert_called_once_with(ANY, pos_arg, foo="bar")

    @patch(
        "opentelemetry.exporter.otlp.proto.common.exporter._create_exp_backoff_with_jitter_generator",
        return_value=repeat(0),
    )
    def test_export_retry(self, mock_backoff):
        """
        Test we retry until success/failure.
        """
        side_effect = [
            RetryableExportError,
            RetryableExportError,
            result_type.SUCCESS,
        ]
        export_func = Mock(side_effect=side_effect)
        exporter = RetryingExporter(export_func, result_type)

        with self.subTest("Retry until success"):
            result = exporter.export_with_retry(10)
            self.assertEqual(export_func.call_count, len(side_effect))
            self.assertIs(result, result_type.SUCCESS)

        with self.subTest("Retry until failure"):
            export_func.reset_mock()
            side_effect.insert(0, RetryableExportError)
            side_effect[-1] = result_type.FAILURE
            export_func.configure_mock(side_effect=side_effect)
            result = exporter.export_with_retry(10)
            self.assertEqual(export_func.call_count, len(side_effect))
            self.assertIs(result, result_type.FAILURE)

    @patch(
        "opentelemetry.exporter.otlp.proto.common.exporter._create_exp_backoff_with_jitter_generator",
        return_value=repeat(0.25),
    )
    def test_export_uses_retry_delay(self, mock_backoff):
        """
        Test we retry using the delay specified in the RPC error as a lower bound.
        """
        side_effects = [
            RetryableExportError(0),
            RetryableExportError(0.25),
            RetryableExportError(0.75),
            RetryableExportError(1),
            result_type.SUCCESS,
        ]

        class ExportDelayRecorder(_ExportProtocol):
            def __init__(self):
                self.delays_s = []
                self.prev_call_time = None
                self.mock = Mock(side_effect=side_effects)

            def __call__(self, timeout_s, *args, **kwargs):
                now = time.time()
                if self.prev_call_time is not None:
                    self.delays_s.append(now - self.prev_call_time)
                self.prev_call_time = now
                return self.mock(timeout_s, *args, **kwargs)

        export_func = ExportDelayRecorder()
        exporter = RetryingExporter(export_func, result_type)

        with patch.object(exporter._shutdown_event, 'sleep'):
            result = exporter.export_with_retry(timeout_s=10, foo="bar")
        self.assertIs(result, result_type.SUCCESS)
        self.assertEqual(export_func.mock.call_count, len(side_effects))
        self.assertAlmostEqual(export_func.delays_s[0], 0.25, places=2)
        self.assertAlmostEqual(export_func.delays_s[1], 0.25, places=2)
        self.assertAlmostEqual(export_func.delays_s[2], 0.75, places=2)
        self.assertAlmostEqual(export_func.delays_s[3], 1.00, places=2)

    # def
