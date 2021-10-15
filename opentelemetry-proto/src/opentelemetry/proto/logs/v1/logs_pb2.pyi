"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.internal.enum_type_wrapper
import google.protobuf.message
import opentelemetry.proto.common.v1.common_pb2
import opentelemetry.proto.resource.v1.resource_pb2
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor = ...

class SeverityNumber(_SeverityNumber, metaclass=_SeverityNumberEnumTypeWrapper):
    """Possible values for LogRecord.SeverityNumber."""
    pass
class _SeverityNumber:
    V = typing.NewType('V', builtins.int)
class _SeverityNumberEnumTypeWrapper(google.protobuf.internal.enum_type_wrapper._EnumTypeWrapper[_SeverityNumber.V], builtins.type):
    DESCRIPTOR: google.protobuf.descriptor.EnumDescriptor = ...
    SEVERITY_NUMBER_UNSPECIFIED = SeverityNumber.V(0)
    """UNSPECIFIED is the default SeverityNumber, it MUST NOT be used."""

    SEVERITY_NUMBER_TRACE = SeverityNumber.V(1)
    SEVERITY_NUMBER_TRACE2 = SeverityNumber.V(2)
    SEVERITY_NUMBER_TRACE3 = SeverityNumber.V(3)
    SEVERITY_NUMBER_TRACE4 = SeverityNumber.V(4)
    SEVERITY_NUMBER_DEBUG = SeverityNumber.V(5)
    SEVERITY_NUMBER_DEBUG2 = SeverityNumber.V(6)
    SEVERITY_NUMBER_DEBUG3 = SeverityNumber.V(7)
    SEVERITY_NUMBER_DEBUG4 = SeverityNumber.V(8)
    SEVERITY_NUMBER_INFO = SeverityNumber.V(9)
    SEVERITY_NUMBER_INFO2 = SeverityNumber.V(10)
    SEVERITY_NUMBER_INFO3 = SeverityNumber.V(11)
    SEVERITY_NUMBER_INFO4 = SeverityNumber.V(12)
    SEVERITY_NUMBER_WARN = SeverityNumber.V(13)
    SEVERITY_NUMBER_WARN2 = SeverityNumber.V(14)
    SEVERITY_NUMBER_WARN3 = SeverityNumber.V(15)
    SEVERITY_NUMBER_WARN4 = SeverityNumber.V(16)
    SEVERITY_NUMBER_ERROR = SeverityNumber.V(17)
    SEVERITY_NUMBER_ERROR2 = SeverityNumber.V(18)
    SEVERITY_NUMBER_ERROR3 = SeverityNumber.V(19)
    SEVERITY_NUMBER_ERROR4 = SeverityNumber.V(20)
    SEVERITY_NUMBER_FATAL = SeverityNumber.V(21)
    SEVERITY_NUMBER_FATAL2 = SeverityNumber.V(22)
    SEVERITY_NUMBER_FATAL3 = SeverityNumber.V(23)
    SEVERITY_NUMBER_FATAL4 = SeverityNumber.V(24)

SEVERITY_NUMBER_UNSPECIFIED = SeverityNumber.V(0)
"""UNSPECIFIED is the default SeverityNumber, it MUST NOT be used."""

SEVERITY_NUMBER_TRACE = SeverityNumber.V(1)
SEVERITY_NUMBER_TRACE2 = SeverityNumber.V(2)
SEVERITY_NUMBER_TRACE3 = SeverityNumber.V(3)
SEVERITY_NUMBER_TRACE4 = SeverityNumber.V(4)
SEVERITY_NUMBER_DEBUG = SeverityNumber.V(5)
SEVERITY_NUMBER_DEBUG2 = SeverityNumber.V(6)
SEVERITY_NUMBER_DEBUG3 = SeverityNumber.V(7)
SEVERITY_NUMBER_DEBUG4 = SeverityNumber.V(8)
SEVERITY_NUMBER_INFO = SeverityNumber.V(9)
SEVERITY_NUMBER_INFO2 = SeverityNumber.V(10)
SEVERITY_NUMBER_INFO3 = SeverityNumber.V(11)
SEVERITY_NUMBER_INFO4 = SeverityNumber.V(12)
SEVERITY_NUMBER_WARN = SeverityNumber.V(13)
SEVERITY_NUMBER_WARN2 = SeverityNumber.V(14)
SEVERITY_NUMBER_WARN3 = SeverityNumber.V(15)
SEVERITY_NUMBER_WARN4 = SeverityNumber.V(16)
SEVERITY_NUMBER_ERROR = SeverityNumber.V(17)
SEVERITY_NUMBER_ERROR2 = SeverityNumber.V(18)
SEVERITY_NUMBER_ERROR3 = SeverityNumber.V(19)
SEVERITY_NUMBER_ERROR4 = SeverityNumber.V(20)
SEVERITY_NUMBER_FATAL = SeverityNumber.V(21)
SEVERITY_NUMBER_FATAL2 = SeverityNumber.V(22)
SEVERITY_NUMBER_FATAL3 = SeverityNumber.V(23)
SEVERITY_NUMBER_FATAL4 = SeverityNumber.V(24)
global___SeverityNumber = SeverityNumber


class LogRecordFlags(_LogRecordFlags, metaclass=_LogRecordFlagsEnumTypeWrapper):
    """Masks for LogRecord.flags field."""
    pass
class _LogRecordFlags:
    V = typing.NewType('V', builtins.int)
class _LogRecordFlagsEnumTypeWrapper(google.protobuf.internal.enum_type_wrapper._EnumTypeWrapper[_LogRecordFlags.V], builtins.type):
    DESCRIPTOR: google.protobuf.descriptor.EnumDescriptor = ...
    LOG_RECORD_FLAG_UNSPECIFIED = LogRecordFlags.V(0)
    LOG_RECORD_FLAG_TRACE_FLAGS_MASK = LogRecordFlags.V(255)

LOG_RECORD_FLAG_UNSPECIFIED = LogRecordFlags.V(0)
LOG_RECORD_FLAG_TRACE_FLAGS_MASK = LogRecordFlags.V(255)
global___LogRecordFlags = LogRecordFlags


class ResourceLogs(google.protobuf.message.Message):
    """A collection of InstrumentationLibraryLogs from a Resource."""
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    RESOURCE_FIELD_NUMBER: builtins.int
    INSTRUMENTATION_LIBRARY_LOGS_FIELD_NUMBER: builtins.int
    SCHEMA_URL_FIELD_NUMBER: builtins.int
    @property
    def resource(self) -> opentelemetry.proto.resource.v1.resource_pb2.Resource:
        """The resource for the logs in this message.
        If this field is not set then resource info is unknown.
        """
        pass
    @property
    def instrumentation_library_logs(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___InstrumentationLibraryLogs]:
        """A list of InstrumentationLibraryLogs that originate from a resource."""
        pass
    schema_url: typing.Text = ...
    """This schema_url applies to the data in the "resource" field. It does not apply
    to the data in the "instrumentation_library_logs" field which have their own
    schema_url field.
    """

    def __init__(self,
        *,
        resource : typing.Optional[opentelemetry.proto.resource.v1.resource_pb2.Resource] = ...,
        instrumentation_library_logs : typing.Optional[typing.Iterable[global___InstrumentationLibraryLogs]] = ...,
        schema_url : typing.Text = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["resource",b"resource"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["instrumentation_library_logs",b"instrumentation_library_logs","resource",b"resource","schema_url",b"schema_url"]) -> None: ...
global___ResourceLogs = ResourceLogs

class InstrumentationLibraryLogs(google.protobuf.message.Message):
    """A collection of Logs produced by an InstrumentationLibrary."""
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    INSTRUMENTATION_LIBRARY_FIELD_NUMBER: builtins.int
    LOGS_FIELD_NUMBER: builtins.int
    SCHEMA_URL_FIELD_NUMBER: builtins.int
    @property
    def instrumentation_library(self) -> opentelemetry.proto.common.v1.common_pb2.InstrumentationLibrary:
        """The instrumentation library information for the logs in this message.
        Semantically when InstrumentationLibrary isn't set, it is equivalent with
        an empty instrumentation library name (unknown).
        """
        pass
    @property
    def logs(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[global___LogRecord]:
        """A list of log records."""
        pass
    schema_url: typing.Text = ...
    """This schema_url applies to all logs in the "logs" field."""

    def __init__(self,
        *,
        instrumentation_library : typing.Optional[opentelemetry.proto.common.v1.common_pb2.InstrumentationLibrary] = ...,
        logs : typing.Optional[typing.Iterable[global___LogRecord]] = ...,
        schema_url : typing.Text = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["instrumentation_library",b"instrumentation_library"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["instrumentation_library",b"instrumentation_library","logs",b"logs","schema_url",b"schema_url"]) -> None: ...
global___InstrumentationLibraryLogs = InstrumentationLibraryLogs

class LogRecord(google.protobuf.message.Message):
    """A log record according to OpenTelemetry Log Data Model:
    https://github.com/open-telemetry/oteps/blob/main/text/logs/0097-log-data-model.md
    """
    DESCRIPTOR: google.protobuf.descriptor.Descriptor = ...
    TIME_UNIX_NANO_FIELD_NUMBER: builtins.int
    SEVERITY_NUMBER_FIELD_NUMBER: builtins.int
    SEVERITY_TEXT_FIELD_NUMBER: builtins.int
    NAME_FIELD_NUMBER: builtins.int
    BODY_FIELD_NUMBER: builtins.int
    ATTRIBUTES_FIELD_NUMBER: builtins.int
    DROPPED_ATTRIBUTES_COUNT_FIELD_NUMBER: builtins.int
    FLAGS_FIELD_NUMBER: builtins.int
    TRACE_ID_FIELD_NUMBER: builtins.int
    SPAN_ID_FIELD_NUMBER: builtins.int
    time_unix_nano: builtins.int = ...
    """time_unix_nano is the time when the event occurred.
    Value is UNIX Epoch time in nanoseconds since 00:00:00 UTC on 1 January 1970.
    Value of 0 indicates unknown or missing timestamp.
    """

    severity_number: global___SeverityNumber.V = ...
    """Numerical value of the severity, normalized to values described in Log Data Model.
    [Optional].
    """

    severity_text: typing.Text = ...
    """The severity text (also known as log level). The original string representation as
    it is known at the source. [Optional].
    """

    name: typing.Text = ...
    """Short event identifier that does not contain varying parts. Name describes
    what happened (e.g. "ProcessStarted"). Recommended to be no longer than 50
    characters. Not guaranteed to be unique in any way. [Optional].
    """

    @property
    def body(self) -> opentelemetry.proto.common.v1.common_pb2.AnyValue:
        """A value containing the body of the log record. Can be for example a human-readable
        string message (including multi-line) describing the event in a free form or it can
        be a structured data composed of arrays and maps of other values. [Optional].
        """
        pass
    @property
    def attributes(self) -> google.protobuf.internal.containers.RepeatedCompositeFieldContainer[opentelemetry.proto.common.v1.common_pb2.KeyValue]:
        """Additional attributes that describe the specific event occurrence. [Optional]."""
        pass
    dropped_attributes_count: builtins.int = ...
    flags: builtins.int = ...
    """Flags, a bit field. 8 least significant bits are the trace flags as
    defined in W3C Trace Context specification. 24 most significant bits are reserved
    and must be set to 0. Readers must not assume that 24 most significant bits
    will be zero and must correctly mask the bits when reading 8-bit trace flag (use
    flags & TRACE_FLAGS_MASK). [Optional].
    """

    trace_id: builtins.bytes = ...
    """A unique identifier for a trace. All logs from the same trace share
    the same `trace_id`. The ID is a 16-byte array. An ID with all zeroes
    is considered invalid. Can be set for logs that are part of request processing
    and have an assigned trace id. [Optional].
    """

    span_id: builtins.bytes = ...
    """A unique identifier for a span within a trace, assigned when the span
    is created. The ID is an 8-byte array. An ID with all zeroes is considered
    invalid. Can be set for logs that are part of a particular processing span.
    If span_id is present trace_id SHOULD be also present. [Optional].
    """

    def __init__(self,
        *,
        time_unix_nano : builtins.int = ...,
        severity_number : global___SeverityNumber.V = ...,
        severity_text : typing.Text = ...,
        name : typing.Text = ...,
        body : typing.Optional[opentelemetry.proto.common.v1.common_pb2.AnyValue] = ...,
        attributes : typing.Optional[typing.Iterable[opentelemetry.proto.common.v1.common_pb2.KeyValue]] = ...,
        dropped_attributes_count : builtins.int = ...,
        flags : builtins.int = ...,
        trace_id : builtins.bytes = ...,
        span_id : builtins.bytes = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["body",b"body"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["attributes",b"attributes","body",b"body","dropped_attributes_count",b"dropped_attributes_count","flags",b"flags","name",b"name","severity_number",b"severity_number","severity_text",b"severity_text","span_id",b"span_id","time_unix_nano",b"time_unix_nano","trace_id",b"trace_id"]) -> None: ...
global___LogRecord = LogRecord
