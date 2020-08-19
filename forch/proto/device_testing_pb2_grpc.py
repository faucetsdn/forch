# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from forch.proto.grpc import device_testing_pb2 as forch_dot_proto_dot_grpc_dot_device__testing__pb2
from forch.proto import shared_constants_pb2 as forch_dot_proto_dot_shared__constants__pb2


class DeviceTestingStub(object):
    """
    gRPC service to receive testing results
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ReportTestingResult = channel.unary_unary(
                '/DeviceTesting/ReportTestingResult',
                request_serializer=forch_dot_proto_dot_grpc_dot_device__testing__pb2.DeviceTestingResult.SerializeToString,
                response_deserializer=forch_dot_proto_dot_shared__constants__pb2.Empty.FromString,
                )


class DeviceTestingServicer(object):
    """
    gRPC service to receive testing results
    """

    def ReportTestingResult(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_DeviceTestingServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ReportTestingResult': grpc.unary_unary_rpc_method_handler(
                    servicer.ReportTestingResult,
                    request_deserializer=forch_dot_proto_dot_grpc_dot_device__testing__pb2.DeviceTestingResult.FromString,
                    response_serializer=forch_dot_proto_dot_shared__constants__pb2.Empty.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'DeviceTesting', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class DeviceTesting(object):
    """
    gRPC service to receive testing results
    """

    @staticmethod
    def ReportTestingResult(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/DeviceTesting/ReportTestingResult',
            forch_dot_proto_dot_grpc_dot_device__testing__pb2.DeviceTestingResult.SerializeToString,
            forch_dot_proto_dot_shared__constants__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
