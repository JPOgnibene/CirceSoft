#!/usr/bin/env bash
set -euo pipefail
# Generate Python code from .proto into the protos/ package
# Requires protoc installed and python -m pip install protobuf

PROTO_DIR="protos"
python - <<'PY'
import os
p = os.path.join("protos", "__init__.py")
if not os.path.exists(p):
    open(p, "w").write("")
print("Ensured protos/__init__.py exists")
PY

protoc \
  --python_out=protos \
  --pyi_out=protos \
  -I protos \
  protos/circesoft.proto

echo "Generated protos/circesoft_pb2.py"
