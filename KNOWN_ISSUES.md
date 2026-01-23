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
# Use both compose files to properly configure GPU backend
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile gpu up -d
```

The `docker-compose.gpu.yml` override file:
- Sets `MINERU_BACKEND=pipeline` for the brain-mvp app (see note below about VLM backends)
- Removes the Model Runner URL configuration
- Adds proper dependency on the GPU MinerU service
- Configures GPU memory utilization for cards with 8GB VRAM

This requires:
- NVIDIA GPU with compute capability 8.0+ (Ampere/Ada/Hopper)
- NVIDIA Container Toolkit installed
- Linux or WSL2 on Windows

**Tested Configurations:**
- RTX 3060 Ti (8GB VRAM) - use `VLLM_GPU_MEMORY_UTILIZATION=0.85`
- RTX 3060 (12GB VRAM) - use `VLLM_GPU_MEMORY_UTILIZATION=0.90`
- RTX 3090/4090 (24GB VRAM) - default settings work well

---

---

## MinerU API Known Issues (GPU Profile)

### Issue 1: Duplicate Backend Parameter Error

**Symptom:**
```
MinerU API returned status 500: {"error":"Failed to process file: mineru.cli.common.aio_do_parse() got multiple values for keyword argument 'backend'"}
```

**Cause:** When MinerU API is started with `--backend` CLI argument AND receives `backend` in the request body, the internal function receives the parameter twice.

**Solution:** Don't pass `--backend` to the MinerU API CLI. Instead, pass the backend in each request. This is handled automatically by the `docker-compose.gpu.yml` configuration.

### Issue 2: VLM Backend Async Mode Error

**Symptom:**
```
{"error":"Failed to process file: vlm-vllm-engine backend is not supported in async mode, please use vlm-vllm-async-engine backend"}
```

**Cause:** The `vlm-vllm-engine` backend is designed for synchronous CLI usage, not for the async FastAPI server.

**Solution:** Use `vlm-vllm-async-engine` for API calls, or use the `pipeline` backend which works reliably.

### Issue 3: PyTorch Version Conflict with GPU Backends

**Symptom:**
```
{"error":"Failed to process file: Tried to instantiate class '_core_C.ScalarType', but it does not exist!"}
```

**Cause:** vLLM 0.6.1 requires `torch==2.4.0`, but MinerU installs `torch 2.9.1`. This version mismatch causes errors when using `vlm-auto-engine` or `hybrid-auto-engine` backends.

**Solution:** Use the `pipeline` backend instead. It provides reliable PDF processing with layout detection, OCR, and table extraction without the VLM components. The current GPU configuration uses `pipeline` by default.

### Valid MinerU API Backends

| Backend | Description | Status |
|---------|-------------|--------|
| `pipeline` | CPU-based with GPU-accelerated OCR | **Recommended** |
| `vlm-auto-engine` | Local GPU VLM processing | Broken (PyTorch conflict) |
| `vlm-http-client` | External VLM API | Works with external server |
| `hybrid-auto-engine` | Next-gen local processing | Broken (PyTorch conflict) |
| `hybrid-http-client` | External VLM + local processing | Works with external server |

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

## Abbreviation Expansion - Duplicate Expansion Bug

### Issue Description

When abbreviations are expanded, some abbreviations may be expanded multiple times in the output, resulting in duplicated expansions like:

```
"The AI (Artificial Intelligence) (Artificial Intelligence) (Artificial Intelligence) field..."
```

Instead of the expected:

```
"The AI (Artificial Intelligence) field..."
```

### Symptoms

- Abbreviations appear with multiple parenthetical expansions
- The duplication count varies (sometimes 2x, sometimes 3x)
- Affects abbreviations that appear multiple times in the original text

### Root Cause

The `AbbreviationExpander` may be processing already-expanded text, causing it to re-expand abbreviations that were already expanded in a previous pass. This can happen when:
1. The expander runs multiple passes over the text
2. The expanded text is used as input for subsequent processing

### Workaround

The feature still works correctly for RAG purposes - the expanded text contains the full terms and will be searchable. The duplication is cosmetic and does not affect retrieval accuracy.

### Status

**Priority**: Low
**Status**: Known issue, fix pending

### Planned Fix

- Add detection to skip already-expanded abbreviations (check for pattern `ABBREV (Expansion)`)
- Implement single-pass expansion to avoid re-processing
- Add unit tests for edge cases

---

## Reporting New Issues

If you encounter issues not covered here, please:
1. Check the logs: `docker compose logs -f brain-mvp`
2. Check MinerU logs: `docker compose logs -f mineru-api`
3. Report issues at: https://github.com/nchen01/brain-mvp/issues
