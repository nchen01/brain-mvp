# MinerU Docker Image with vLLM support
# Based on official MinerU docker configuration
# Requires NVIDIA GPU with Ampere/Ada/Hopper architecture (compute capability 8.0+)
#
# Tested configurations:
# - RTX 3060 Ti (8GB VRAM, CC 8.6) - use VLLM_GPU_MEMORY_UTILIZATION=0.85
# - RTX 3060 (12GB VRAM, CC 8.6) - use VLLM_GPU_MEMORY_UTILIZATION=0.90
# - RTX 3090/4090 (24GB VRAM) - default settings work well

FROM vllm/vllm-openai:v0.6.1.post2

# Install system dependencies for font rendering and OpenCV
RUN apt-get update && apt-get install -y \
    fonts-noto-core \
    fonts-noto-cjk \
    fontconfig \
    libgl1 \
    curl \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# Install MinerU with core dependencies
RUN python3 -m pip install -U 'mineru[core]>=2.0.0' && \
    python3 -m pip cache purge

# Download all MinerU models from HuggingFace (this takes a while)
RUN mineru-models-download -s huggingface -m all

# Create working directories
RUN mkdir -p /pdfs /vllm-workspace/output

# Set environment and entrypoint
ENV MINERU_MODEL_SOURCE=local

ENTRYPOINT ["/bin/bash", "-c", "export MINERU_MODEL_SOURCE=local && exec \"$@\"", "--"]
