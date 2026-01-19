# Known Issues

This document describes known issues, attempted solutions, and workarounds for the Brain MVP project.

---

## Mac Docker Model Runner - Vision/Multimodal Support

### Issue Description

Docker Desktop's Model Runner feature on macOS does not properly support vision/multimodal capabilities required by MinerU's VLM (Vision Language Model) backends. When using the `mac-modelrunner` profile, MinerU's `vlm-http-client` backend fails to process images because Docker Model Runner:

1. **Does not load the mmproj (multimodal projection) file** - The Model Runner loads GGUF models but doesn't automatically include the vision projection weights needed for image understanding.
2. **Lacks explicit vision endpoint configuration** - The OpenAI-compatible API exposed by Model Runner doesn't support the `/v1/chat/completions` with image inputs in the expected format.
3. **Model format limitations** - Docker Model Runner uses llama.cpp internally but doesn't expose all llama.cpp server options for vision models.

### Symptoms

When attempting to use MinerU with Docker Model Runner:

```
MinerU API error: VLM backend failed to process image
Falling back to AdvancedPDFProcessor
```

Or in MinerU logs:

```
Error: Vision model endpoint not available
Error: Failed to encode image for VLM processing
```

### What Was Attempted

1. **Using Docker Model Runner's default configuration**
   - Result: Model loads but cannot process images
   - The `/engines/llama.cpp` endpoint works for text but not multimodal

2. **Setting `MINERU_SERVER_URL` to Docker Model Runner endpoint**
   ```yaml
   MINERU_SERVER_URL: http://model-runner.docker.internal/engines/llama.cpp
   ```
   - Result: Text generation works, but image inputs fail

3. **Trying different GGUF vision models via Docker Model Runner**
   - Models like `llava`, `bakllava`, `moondream` were tested
   - Result: Same issue - mmproj weights not loaded

4. **Using the `vlm-http-client` backend with various configurations**
   - Result: Backend expects OpenAI-compatible vision API which Model Runner doesn't fully implement

---

## Solutions

### Solution 1: Run llama.cpp Server Directly with mmproj (Recommended for Mac)

The most reliable solution is to run a llama.cpp server yourself on the host machine with the multimodal projection file explicitly loaded.

#### Step 1: Install llama.cpp

```bash
# Using Homebrew (macOS)
brew install llama.cpp

# Or build from source
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j

# For Apple Silicon with Metal support
make LLAMA_METAL=1 -j
```

#### Step 2: Download a Vision Model and mmproj File

Download a vision-capable model and its corresponding mmproj file:

```bash
# Example: LLaVA 1.6 Mistral (recommended for quality)
# Download the main model
wget https://huggingface.co/cjpais/llava-1.6-mistral-7b-gguf/resolve/main/llava-v1.6-mistral-7b.Q4_K_M.gguf

# Download the mmproj file (REQUIRED for vision)
wget https://huggingface.co/cjpais/llava-1.6-mistral-7b-gguf/resolve/main/mmproj-model-f16.gguf

# Alternative: Smaller model (faster, less accurate)
# MobileVLM
wget https://huggingface.co/mys/ggml_MobileVLM/resolve/main/MobileVLM-3B-Q4_K.gguf
wget https://huggingface.co/mys/ggml_MobileVLM/resolve/main/MobileVLM-3B-mmproj-f16.gguf
```

#### Step 3: Start the llama.cpp Server with Vision Support

```bash
# Start server with BOTH the main model AND mmproj file
llama-server \
  --model llava-v1.6-mistral-7b.Q4_K_M.gguf \
  --mmproj mmproj-model-f16.gguf \
  --host 0.0.0.0 \
  --port 8001 \
  --ctx-size 4096 \
  --n-gpu-layers 99  # Use GPU acceleration on Apple Silicon

# Or with the llama.cpp build directory
./llama-server \
  -m ./models/llava-v1.6-mistral-7b.Q4_K_M.gguf \
  --mmproj ./models/mmproj-model-f16.gguf \
  -c 4096 \
  --host 0.0.0.0 \
  --port 8001
```

**Critical**: The `--mmproj` flag is **required** for vision capabilities. Without it, the model will only process text.

#### Step 4: Configure Brain MVP to Use Your Server

Update `docker-compose.yml` or set environment variables:

```yaml
environment:
  MINERU_BACKEND: vlm-http-client
  MINERU_SERVER_URL: http://host.docker.internal:8001
```

Or in `.env`:

```bash
MINERU_BACKEND=vlm-http-client
MINERU_SERVER_URL=http://host.docker.internal:8001
```

#### Step 5: Verify the Setup

Test the vision endpoint:

```bash
# Test text generation
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'

# Test vision (with base64 image)
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }],
    "max_tokens": 100
  }'
```

---

### Solution 2: Use the CPU Profile (No Vision, But Works)

If you don't need vision-based PDF processing, use the CPU profile which runs MinerU's pipeline backend:

```bash
docker compose --profile cpu up -d
```

This uses traditional layout detection and OCR without VLM capabilities. It's slower and less accurate for complex layouts but works reliably on Mac.

---

### Solution 3: Use an External VLM API Service

Configure MinerU to use an external OpenAI-compatible vision API:

```yaml
environment:
  MINERU_BACKEND: vlm-http-client
  MINERU_SERVER_URL: https://api.openai.com/v1  # Or any compatible service
  OPENAI_API_KEY: your_api_key
```

Supported services:
- OpenAI GPT-4 Vision
- Azure OpenAI
- Anthropic Claude (via compatible proxy)
- Local Ollama with vision models

---

### Solution 4: Use NVIDIA GPU (Linux/Windows)

If you have access to an NVIDIA GPU, use the GPU profile for best performance:

```bash
docker compose --profile gpu up -d
```

This requires:
- NVIDIA GPU with compute capability 8.0+ (Ampere/Ada/Hopper)
- NVIDIA Container Toolkit installed
- Linux or WSL2 on Windows

---

## Summary of Mac Options

| Option | Vision Support | Performance | Complexity |
|--------|---------------|-------------|------------|
| **llama.cpp with mmproj** | Yes | Good (Metal) | Medium |
| **CPU Profile** | No | Slow | Easy |
| **External API** | Yes | Fast | Easy (costs $) |
| **Docker Model Runner** | No* | N/A | N/A |

*Docker Model Runner cannot currently be used for vision tasks due to mmproj loading limitations.

---

## Additional Resources

- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [llama.cpp Server Documentation](https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md)
- [MinerU Documentation](https://github.com/opendatalab/MinerU)
- [Supported Vision Models for llama.cpp](https://github.com/ggerganov/llama.cpp/blob/master/examples/llava/README.md)

---

## Reporting New Issues

If you encounter issues not covered here, please:
1. Check the logs: `docker compose logs -f brain-mvp`
2. Check MinerU logs: `docker compose logs -f mineru-api`
3. Report issues at: https://github.com/nchen01/brain-mvp/issues
