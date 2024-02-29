import unittest
from logging import WARNING
from unittest.mock import Mock, ANY

from opentelemetry.exporter.otlp.proto.common.exporter import (
    ExportResult,
    RetryingExporter,
    _DEFAULT_EXPORT_TIMEOUT_S,
)

result_type = Mock()


class TestRetryableExporter(unittest.TestCase):
    def test_export_non_retryable(self):
        export_func = Mock()
        exporter = RetryingExporter(
            export_func, result_type, _DEFAULT_EXPORT_TIMEOUT_S
        )
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
            export_func.assert_called_once_with(pos_arg, timeout_s = ANY, foo="bar")

        with self.subTest("Export Fail"):
            export_func.reset_mock()
            export_func.configure_mock(return_value=result_type.FAILURE)
            pos_arg = Mock()
            with self.assertRaises(AssertionError):
                with self.assertLogs(level=WARNING):
                    result = exporter.export_with_retry(
                        _DEFAULT_EXPORT_TIMEOUT_S, pos_arg, foo="bar"
                    )
            self.assertIs(result, result_type.FAILURE)
            export_func.assert_called_once_with(pos_arg, timeout_s = ANY, foo="bar")

    def test_export
