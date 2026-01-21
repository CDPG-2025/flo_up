# Windows PowerShell script to generate protobuf files
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ./grpc.proto

# Replace 'grpc_pb2' with 'proto.grpc_pb2' in the generated file
(Get-Content grpc_pb2_grpc.py -Raw) -replace 'grpc_pb2', 'proto.grpc_pb2' | Set-Content grpc_pb2_grpc.py

Write-Host "Protobuf files generated successfully!" -ForegroundColor Green
