#!/bin/bash
rm -rf ./vllm-main
git clone --branch main https://github.com/vllm-project/vllm ./vllm-main
cp app.py ./vllm-main
mv ./vllm-main/Dockerfile.cpu ./vllm-main/Dockerfile.cpu.back
cp Dockerfile.cpu.modified ./vllm-main/Dockerfile.cpu
