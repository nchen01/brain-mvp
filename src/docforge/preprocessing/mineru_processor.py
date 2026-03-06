"""MinerU PDF processor for extracting text, images, and tables from PDFs.

This processor calls the MinerU API service for high-quality PDF parsing
with layout detection, OCR support, and table extraction.

MinerU API: https://github.com/opendatalab/MinerU
"""

import logging
import os
import time
import httpx
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import json
import base64

from .base_processor import BaseDocumentProcessor
from .schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingMetadata,
    ProcessingStatus,
    TableData,
    ImageData,
    create_content_element,
    create_processing_metadata,
    create_document_structure,
    create_table_data,
    create_image_data
)

logger = logging.getLogger(__name__)


class MinerUProcessor(BaseDocumentProcessor):
    """
    MinerU API-based PDF processor for high-quality document extraction.

    Features:
    - Layout detection using DocLayout-YOLO
    - OCR support via PaddleOCR (109 languages)
    - Table structure recognition
    - Image extraction
    - Formula recognition (UniMERNet)
    - GPU acceleration via VLM-VLLM backend

    Falls back to AdvancedPDFProcessor if MinerU API is not available.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the MinerU processor."""
        super().__init__(config)
        self.processor_name = "MinerUProcessor"
        self.processor_version = "2.1.0"  # API version

        # API configuration
        self.api_url = self.config.get(
            "api_url",
            os.environ.get("MINERU_API_URL", "http://mineru-api:8080")
        )
        self.api_enabled = self.config.get(
            "api_enabled",
            os.environ.get("MINERU_API_ENABLED", "true").lower() == "true"
        )
        self.api_timeout = self.config.get("api_timeout", 300)  # 5 minutes default

        # Processing options
        self.extract_images = self.config.get("extract_images", True)
        self.extract_tables = self.config.get("extract_tables", True)
        self.ocr_enabled = self.config.get("ocr_enabled", True)
        self.language = self.config.get("language", "auto")
        self.output_dir = self.config.get("output_dir", "./data/mineru_output")

        # Backend configuration (pipeline, vlm-http-client, vlm-vllm-engine, etc.)
        # If MINERU_BACKEND is empty or not set, don't send backend in request (let API use its default)
        self.backend = self.config.get(
            "backend",
            os.environ.get("MINERU_BACKEND", "")
        )

        # VLM server URL (for vlm-http-client and hybrid-http-client backends)
        # Use MINERU_SERVER_URL without path suffixes - MinerU handles the paths
        self.vlm_http_url = self.config.get(
            "vlm_http_url",
            os.environ.get("MINERU_SERVER_URL", os.environ.get("VLM_HTTP_BASE_URL", ""))
        )

        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Initialize fallback processor lazily
        self._fallback_processor = None
        self._api_available = None  # Cache API availability check

        logger.info(f"MinerU processor initialized - API URL: {self.api_url}, Backend: {self.backend}")

    @property
    def fallback_processor(self):
        """Lazy-load the fallback processor."""
        if self._fallback_processor is None:
            from .advanced_pdf_processor import AdvancedPDFProcessor
            self._fallback_processor = AdvancedPDFProcessor(self.config)
            logger.info("Fallback processor (AdvancedPDFProcessor) initialized")
        return self._fallback_processor

    def is_available(self) -> bool:
        """Check if MinerU API is available."""
        if not self.api_enabled:
            return False

        # Use cached result only if confirmed available (True).
        # Do NOT cache False — MinerU may still be loading models at startup,
        # so a failed check must be re-tried on the next request.
        if self._api_available is True:
            return True

        try:
            with httpx.Client(timeout=5.0) as client:
                # MinerU API doesn't have /health, check /openapi.json instead
                response = client.get(f"{self.api_url}/openapi.json")
                if response.status_code == 200:
                    self._api_available = True
                    logger.info("MinerU API is available")
                else:
                    logger.warning(f"MinerU API returned status {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"MinerU API not available: {e}")
            return False

        return self._api_available

    def get_supported_formats(self) -> List[str]:
        """Get supported PDF formats."""
        return ['.pdf']

    def _process_document(
        self,
        file_path: str,
        file_content: bytes,
        **kwargs
    ) -> StandardizedDocumentOutput:
        """Process a PDF document using MinerU API."""
        start_time = time.time()

        try:
            logger.info(f"Processing PDF with MinerU: {file_path}")

            # Extract metadata
            file_metadata = self._extract_metadata_from_path(file_path)

            # Check API availability and process
            logger.info(f"MinerU API enabled: {self.api_enabled}, checking availability...")
            api_available = self.is_available()
            logger.info(f"MinerU API available: {api_available}")

            if self.api_enabled and api_available:
                try:
                    logger.info("Using MinerU API for processing")
                    mineru_result = self._process_with_api(file_path, file_content)
                    logger.info("MinerU API processing successful")
                except Exception as api_error:
                    logger.error(f"MinerU API error: {api_error}")
                    logger.info("Falling back to AdvancedPDFProcessor")
                    return self.fallback_processor._process_document(file_path, file_content, **kwargs)
            else:
                logger.info("MinerU API not available, using fallback processor")
                return self.fallback_processor._process_document(file_path, file_content, **kwargs)

            # Convert MinerU output to standardized format
            content_elements = self._convert_to_content_elements(mineru_result)
            tables = self._extract_tables_from_result(mineru_result)
            images = self._extract_images_from_result(mineru_result)

            processing_time = time.time() - start_time

            # Create processing metadata
            processing_metadata = create_processing_metadata(
                processor_name=self.processor_name,
                processor_version=self.processor_version,
                processing_duration=processing_time,
                input_file_info=file_metadata,
                processing_parameters={
                    "api_url": self.api_url,
                    "extract_images": self.extract_images,
                    "extract_tables": self.extract_tables,
                    "ocr_enabled": self.ocr_enabled,
                    "language": self.language,
                }
            )

            # Create document structure
            element_counts = {}
            for element in content_elements:
                element_type = element.content_type.value if hasattr(element.content_type, 'value') else str(element.content_type)
                element_counts[element_type] = element_counts.get(element_type, 0) + 1

            document_structure = create_document_structure(
                total_elements=len(content_elements),
                total_pages=mineru_result.get("total_pages", 1),
                element_counts=element_counts,
                has_tables=len(tables) > 0,
                has_images=len(images) > 0,
                language=mineru_result.get("detected_language", "en")
            )

            # Generate text representations
            plain_text = self._generate_plain_text(content_elements)
            markdown_text = mineru_result.get("markdown_content", self._generate_markdown(content_elements, tables, images))

            logger.info(f"MinerU API processing completed in {processing_time:.2f}s - "
                       f"{len(content_elements)} elements, {len(tables)} tables, {len(images)} images")

            return StandardizedDocumentOutput(
                content_elements=content_elements,
                tables=tables,
                images=images,
                document_metadata=file_metadata,
                document_structure=document_structure,
                processing_metadata=processing_metadata,
                processing_status=ProcessingStatus.SUCCESS,
                plain_text=plain_text,
                markdown_text=markdown_text
            )

        except Exception as e:
            logger.error(f"Error processing PDF with MinerU {file_path}: {e}")

            # Attempt fallback to AdvancedPDFProcessor
            logger.info("Attempting fallback to AdvancedPDFProcessor")
            try:
                return self.fallback_processor._process_document(file_path, file_content, **kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback processor also failed: {fallback_error}")
                raise

    def _process_with_api(self, file_path: str, file_content: bytes) -> Dict[str, Any]:
        """
        Process PDF using MinerU API service.

        The API accepts multipart file uploads and returns JSON with extracted content.
        """
        logger.info(f"Sending PDF to MinerU API: {self.api_url}")

        # Prepare the file for upload
        filename = os.path.basename(file_path)

        try:
            with httpx.Client(timeout=self.api_timeout) as client:
                # MinerU API uses /file_parse endpoint with multipart form data
                files = {"files": (filename, file_content, "application/pdf")}

                # Build form data for MinerU API
                data = {
                    "table_enable": str(self.extract_tables).lower(),
                    "return_md": "true",
                    "return_content_list": "true",
                    "return_images": str(self.extract_images).lower(),
                }

                # Only send backend if explicitly configured (non-empty)
                # This avoids "multiple values for keyword argument 'backend'" when
                # MinerU API already has backend set via CLI (e.g., GPU mode)
                if self.backend:
                    data["backend"] = self.backend

                # Add server_url for vlm-http-client and hybrid-http-client backends
                if self.backend in ("vlm-http-client", "hybrid-http-client") and self.vlm_http_url:
                    data["server_url"] = self.vlm_http_url
                    logger.info(f"MinerU API request - backend: {self.backend}, server_url: {self.vlm_http_url}")
                elif self.backend:
                    logger.info(f"MinerU API request - backend: {self.backend}")
                else:
                    logger.info("MinerU API request - using API default backend")

                # Set language if specified
                if self.language != "auto":
                    data["lang_list"] = self.language

                response = client.post(
                    f"{self.api_url}/file_parse",
                    files=files,
                    data=data
                )

                if response.status_code != 200:
                    raise Exception(f"MinerU API returned status {response.status_code}: {response.text}")

                api_result = response.json()

                # Transform API response to our internal format
                return self._transform_api_response(api_result, filename)

        except httpx.TimeoutException:
            raise Exception(f"MinerU API timeout after {self.api_timeout}s")
        except httpx.RequestError as e:
            raise Exception(f"MinerU API request failed: {e}")

    def _transform_api_response(self, api_result: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Transform MinerU API response to our internal format."""

        # MinerU API response format:
        # {
        #   "backend": "pipeline",
        #   "version": "2.7.0",
        #   "results": {
        #     "filename_without_ext": {
        #       "md_content": "...",
        #       "content_list": "[...]"  # JSON string
        #     }
        #   }
        # }

        # Extract file results from nested structure
        results = api_result.get("results", {})

        # Get the file key (filename without extension)
        file_key = Path(filename).stem
        file_result = results.get(file_key, {})

        # If not found by stem, try first key in results
        if not file_result and results:
            file_key = list(results.keys())[0]
            file_result = results[file_key]

        # Get markdown content
        markdown_content = file_result.get("md_content", "")

        # Parse content_list (it's a JSON string)
        content_list_str = file_result.get("content_list", "[]")
        try:
            if isinstance(content_list_str, str):
                content_blocks = json.loads(content_list_str)
            else:
                content_blocks = content_list_str if content_list_str else []
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse content_list JSON: {content_list_str[:100]}")
            content_blocks = []

        result = {
            "total_pages": max([b.get("page_idx", 0) for b in content_blocks], default=0) + 1,
            "detected_language": self.language if self.language != "auto" else "en",
            "content": [],
            "metadata": {
                "title": filename,
                "author": "Unknown",
                "creation_date": "",
                "total_words": 0,
                "total_characters": 0,
                "backend": api_result.get("backend", "pipeline"),
                "mineru_version": api_result.get("version", "unknown")
            },
            "markdown_content": markdown_content,
        }

        # Process content blocks
        for block in content_blocks:
            element = self._convert_api_block(block)
            if element:
                result["content"].append(element)

        # If no structured content but markdown is available, create basic content
        if not result["content"] and result["markdown_content"]:
            result["content"].append({
                "type": "paragraph",
                "text": result["markdown_content"],
                "page": 1,
                "bbox": []
            })

        # Calculate text statistics
        total_words = 0
        total_chars = 0
        for item in result["content"]:
            if "text" in item:
                text = item["text"]
                total_chars += len(text)
                total_words += len(text.split())

        result["metadata"]["total_words"] = total_words
        result["metadata"]["total_characters"] = total_chars

        return result

    def _convert_api_block(self, block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert an API content block to our format."""
        try:
            block_type = block.get("type", block.get("category", "text"))

            # Map MinerU API types to our types
            # MinerU uses: text, title, table, image, etc.
            type_mapping = {
                "text": "paragraph",
                "paragraph": "paragraph",
                "title": "heading",
                "heading": "heading",
                "header": "heading",
                "table": "table",
                "image": "image",
                "figure": "image",
                "equation": "equation",
                "formula": "equation",
                "list": "list",
                "list_item": "list",
            }

            element_type = type_mapping.get(block_type.lower(), "paragraph")

            # MinerU uses page_idx (0-based), convert to page (1-based)
            page_idx = block.get("page_idx", block.get("page", 0))
            if isinstance(page_idx, int):
                page = page_idx + 1
            else:
                page = 1

            element = {
                "type": element_type,
                "text": block.get("text", block.get("content", "")),
                "page": page,
                "bbox": block.get("bbox", block.get("bounding_box", [])),
            }

            # Handle text level (MinerU uses text_level for heading levels)
            text_level = block.get("text_level", 0)
            if text_level == 1 or element_type == "heading":
                element["type"] = "heading"
                element["level"] = text_level if text_level > 0 else 1

            # Handle tables
            if element_type == "table":
                element["table_html"] = block.get("html", block.get("table_html", ""))
                element["table_body"] = block.get("cells", block.get("table_body", []))

            # Handle images
            if element_type == "image":
                element["image_path"] = block.get("path", block.get("img_path", ""))
                element["image_data"] = block.get("base64", block.get("data", ""))
                element["alt_text"] = block.get("alt", f"Image from page {element['page']}")

            return element

        except Exception as e:
            logger.warning(f"Error converting API block: {e}")
            return None

    def _convert_to_content_elements(self, mineru_result: Dict[str, Any]) -> List[ContentElement]:
        """Convert MinerU result to standardized content elements."""
        elements = []

        for i, item in enumerate(mineru_result.get("content", [])):
            element_id = str(uuid.uuid4())

            # Map content types
            content_type_map = {
                "heading": ContentType.HEADING,
                "paragraph": ContentType.PARAGRAPH,
                "text": ContentType.TEXT,
                "list": ContentType.LIST,
                "table": ContentType.TABLE,
                "image": ContentType.IMAGE,
                "code": ContentType.CODE,
                "equation": ContentType.TEXT,
            }

            content_type = content_type_map.get(item.get("type", "text"), ContentType.TEXT)

            # Skip table and image elements (handled separately)
            if content_type in [ContentType.TABLE, ContentType.IMAGE]:
                continue

            # Prepare metadata
            metadata = {
                "page": item.get("page", 1),
                "font_size": item.get("font_size"),
                "font_weight": item.get("font_weight"),
                "source_type": item.get("type")
            }

            # Add level for headings
            if content_type == ContentType.HEADING:
                metadata["level"] = item.get("level", 1)

            element = create_content_element(
                element_id=element_id,
                content_type=content_type,
                content=item.get("text", ""),
                metadata=metadata,
                position={
                    "page": item.get("page", 1),
                    "bbox": item.get("bbox", [])
                },
                formatting={
                    "font_size": item.get("font_size"),
                    "font_weight": item.get("font_weight"),
                    "color": item.get("color")
                }
            )

            elements.append(element)

        return elements

    def _extract_tables_from_result(self, mineru_result: Dict[str, Any]) -> List[TableData]:
        """Extract table data from MinerU result."""
        tables = []

        for item in mineru_result.get("content", []):
            if item.get("type") == "table":
                # Parse table body if available
                table_body = item.get("table_body", [])
                headers = []
                rows = []

                if table_body:
                    if len(table_body) > 0:
                        headers = [str(cell) for cell in table_body[0]]
                        rows = [[str(cell) for cell in row] for row in table_body[1:]]

                table = create_table_data(
                    headers=headers,
                    rows=rows,
                    caption=item.get("caption"),
                    metadata={
                        "page": item.get("page", 1),
                        "bbox": item.get("bbox", []),
                        "table_id": f"table_{len(tables)+1}",
                        "table_html": item.get("table_html", "")
                    }
                )
                tables.append(table)

        return tables

    def _extract_images_from_result(self, mineru_result: Dict[str, Any]) -> List[ImageData]:
        """Extract image data from MinerU result."""
        images = []

        for item in mineru_result.get("content", []):
            if item.get("type") == "image":
                # Save base64 image if provided
                image_path = item.get("image_path", "")
                if not image_path and item.get("image_data"):
                    # Save base64 image to file
                    image_path = self._save_base64_image(
                        item["image_data"],
                        f"image_{len(images)+1}",
                        item.get("page", 1)
                    )

                image = create_image_data(
                    image_id=f"image_{len(images)+1}",
                    file_path=image_path,
                    alt_text=item.get("alt_text", f"Image {len(images)+1}"),
                    caption=item.get("caption"),
                    metadata={
                        "page": item.get("page", 1),
                        "bbox": item.get("bbox", []),
                        "extraction_method": "mineru_api"
                    }
                )
                images.append(image)

        return images

    def _save_base64_image(self, base64_data: str, image_id: str, page: int) -> str:
        """Save a base64-encoded image to file."""
        try:
            # Remove data URL prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            image_bytes = base64.b64decode(base64_data)

            # Determine format from header
            if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                ext = ".png"
            elif image_bytes[:2] == b'\xff\xd8':
                ext = ".jpg"
            else:
                ext = ".png"  # Default to PNG

            image_path = Path(self.output_dir) / f"{image_id}_page{page}{ext}"
            image_path.write_bytes(image_bytes)

            return str(image_path)

        except Exception as e:
            logger.warning(f"Failed to save base64 image: {e}")
            return ""

    def _generate_plain_text(self, content_elements: List[ContentElement]) -> str:
        """Generate plain text from content elements."""
        lines = []

        for element in content_elements:
            if element.content_type in [
                ContentType.TEXT,
                ContentType.PARAGRAPH,
                ContentType.HEADING
            ]:
                if element.content.strip():
                    lines.append(element.content)

        return '\n\n'.join(lines)

    def _generate_markdown(
        self,
        content_elements: List[ContentElement],
        tables: List[TableData],
        images: List[ImageData]
    ) -> str:
        """Generate markdown from all content."""
        lines = []

        # Process content elements
        for element in content_elements:
            if element.content_type == ContentType.HEADING:
                level = element.metadata.get("level", 1) if element.metadata else 1
                lines.append(f"{'#' * level} {element.content}")

            elif element.content_type == ContentType.PARAGRAPH:
                if element.content.strip():
                    lines.append(element.content)

            elif element.content_type == ContentType.LIST:
                lines.append(f"- {element.content}")

            else:
                if element.content.strip():
                    lines.append(element.content)

        # Add tables
        for table in tables:
            if table.caption:
                lines.append(f"**{table.caption}**")

            if table.headers:
                header_row = "| " + " | ".join(table.headers) + " |"
                separator_row = "|" + "|".join([" --- " for _ in table.headers]) + "|"
                lines.append(header_row)
                lines.append(separator_row)

                for row in table.rows:
                    row_text = "| " + " | ".join(str(cell) for cell in row) + " |"
                    lines.append(row_text)

        # Add images
        for image in images:
            alt_text = image.alt_text or f"Image {image.image_id}"
            image_path = image.file_path or f"#{image.image_id}"

            lines.append(f"![{alt_text}]({image_path})")

            if image.caption:
                lines.append(f"*{image.caption}*")

        return '\n\n'.join(lines)

    def validate_config(self) -> List[str]:
        """Validate MinerU processor configuration."""
        errors = super().validate_config()

        # Check if output directory is writable
        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            test_file = output_path / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()

        except Exception as e:
            errors.append(f"Output directory not writable: {e}")

        # Check API availability
        if self.api_enabled and not self.is_available():
            errors.append(f"MinerU API not available at {self.api_url} - will use fallback processor")

        return errors

    def get_processor_info(self) -> Dict[str, Any]:
        """Get processor information."""
        return {
            "name": self.processor_name,
            "version": self.processor_version,
            "api_url": self.api_url,
            "api_enabled": self.api_enabled,
            "api_available": self.is_available() if self.api_enabled else False,
            "supported_formats": self.get_supported_formats(),
            "config": {
                "extract_images": self.extract_images,
                "extract_tables": self.extract_tables,
                "ocr_enabled": self.ocr_enabled,
                "language": self.language,
                "api_timeout": self.api_timeout,
            }
        }

    def reset_api_cache(self):
        """Reset the API availability cache to force a new check."""
        self._api_available = None
