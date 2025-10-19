"""Output format validation and standardization for document processors."""

import logging
import json
import hashlib
from typing import List, Dict, Any, Optional, Union, Set, Tuple
from datetime import datetime, timezone

from .schemas import (
    StandardizedDocumentOutput,
    ContentElement,
    ContentType,
    ProcessingStatus,
    TableData,
    ImageData,
    ProcessingMetadata,
    DocumentStructure
)

logger = logging.getLogger(__name__)


class OutputFormatValidator:
    """Validates and standardizes processor outputs."""
    
    def __init__(self):
        """Initialize the output format validator."""
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_output(self, output: StandardizedDocumentOutput) -> bool:
        """
        Validate a standardized document output.
        
        Args:
            output: The output to validate
            
        Returns:
            True if valid, False otherwise
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        try:
            # Validate required fields
            self._validate_required_fields(output)
            
            # Validate content elements
            self._validate_content_elements(output.content_elements)
            
            # Validate tables
            self._validate_tables(output.tables)
            
            # Validate images
            self._validate_images(output.images)
            
            # Validate document structure
            self._validate_document_structure(output.document_structure)
            
            # Validate processing metadata
            self._validate_processing_metadata(output.processing_metadata)
            
            # Validate text outputs
            self._validate_text_outputs(output)
            
            # Cross-validate consistency
            self._validate_consistency(output)
            
            if self.validation_errors:
                logger.error(f"Output validation failed with {len(self.validation_errors)} errors")
                for error in self.validation_errors:
                    logger.error(f"  - {error}")
                return False
            
            if self.validation_warnings:
                logger.warning(f"Output validation completed with {len(self.validation_warnings)} warnings")
                for warning in self.validation_warnings:
                    logger.warning(f"  - {warning}")
            
            return True
            
        except Exception as e:
            logger.error(f"Output validation failed with exception: {e}")
            self.validation_errors.append(f"Validation exception: {e}")
            return False
    
    def _validate_required_fields(self, output: StandardizedDocumentOutput):
        """Validate that all required fields are present."""
        if not hasattr(output, 'content_elements') or output.content_elements is None:
            self.validation_errors.append("Missing required field: content_elements")
        
        if not hasattr(output, 'tables') or output.tables is None:
            self.validation_errors.append("Missing required field: tables")
        
        if not hasattr(output, 'images') or output.images is None:
            self.validation_errors.append("Missing required field: images")
        
        if not hasattr(output, 'document_metadata') or output.document_metadata is None:
            self.validation_errors.append("Missing required field: document_metadata")
        
        if not hasattr(output, 'document_structure') or output.document_structure is None:
            self.validation_errors.append("Missing required field: document_structure")
        
        if not hasattr(output, 'processing_metadata') or output.processing_metadata is None:
            self.validation_errors.append("Missing required field: processing_metadata")
        
        if not hasattr(output, 'processing_status') or output.processing_status is None:
            self.validation_errors.append("Missing required field: processing_status")
        
        if not hasattr(output, 'plain_text') or output.plain_text is None:
            self.validation_errors.append("Missing required field: plain_text")
        
        if not hasattr(output, 'markdown_text') or output.markdown_text is None:
            self.validation_errors.append("Missing required field: markdown_text")
    
    def _validate_content_elements(self, elements: List[ContentElement]):
        """Validate content elements."""
        if not isinstance(elements, list):
            self.validation_errors.append("content_elements must be a list")
            return
        
        for i, element in enumerate(elements):
            if not hasattr(element, 'element_id') or not element.element_id:
                self.validation_errors.append(f"Content element {i} missing element_id")
            
            if not hasattr(element, 'content_type') or not element.content_type:
                self.validation_errors.append(f"Content element {i} missing content_type")
            
            if not hasattr(element, 'content') or element.content is None:
                self.validation_errors.append(f"Content element {i} missing content")
            
            # Validate content type is valid
            if hasattr(element, 'content_type') and element.content_type:
                valid_types = [ct.value for ct in ContentType] if hasattr(ContentType, '__members__') else []
                if valid_types and element.content_type not in valid_types:
                    self.validation_warnings.append(f"Content element {i} has unknown content_type: {element.content_type}")
    
    def _validate_tables(self, tables: List[TableData]):
        """Validate table data."""
        if not isinstance(tables, list):
            self.validation_errors.append("tables must be a list")
            return
        
        for i, table in enumerate(tables):
            if not hasattr(table, 'headers') or table.headers is None:
                self.validation_errors.append(f"Table {i} missing headers")
            
            if not hasattr(table, 'rows') or table.rows is None:
                self.validation_errors.append(f"Table {i} missing rows")
            
            # Validate table structure consistency
            if hasattr(table, 'headers') and hasattr(table, 'rows') and table.headers and table.rows:
                header_count = len(table.headers)
                for row_idx, row in enumerate(table.rows):
                    if len(row) != header_count:
                        self.validation_warnings.append(
                            f"Table {i}, row {row_idx} has {len(row)} columns but table has {header_count} headers"
                        )
    
    def _validate_images(self, images: List[ImageData]):
        """Validate image data."""
        if not isinstance(images, list):
            self.validation_errors.append("images must be a list")
            return
        
        for i, image in enumerate(images):
            if not hasattr(image, 'image_id') or not image.image_id:
                self.validation_errors.append(f"Image {i} missing image_id")
    
    def _validate_document_structure(self, structure: DocumentStructure):
        """Validate document structure."""
        if not hasattr(structure, 'total_elements') or structure.total_elements is None:
            self.validation_errors.append("Document structure missing total_elements")
        
        if not hasattr(structure, 'total_pages') or structure.total_pages is None:
            self.validation_errors.append("Document structure missing total_pages")
        
        if not hasattr(structure, 'has_tables') or structure.has_tables is None:
            self.validation_errors.append("Document structure missing has_tables")
        
        if not hasattr(structure, 'has_images') or structure.has_images is None:
            self.validation_errors.append("Document structure missing has_images")
    
    def _validate_processing_metadata(self, metadata: ProcessingMetadata):
        """Validate processing metadata."""
        if not hasattr(metadata, 'processor_name') or not metadata.processor_name:
            self.validation_errors.append("Processing metadata missing processor_name")
        
        if not hasattr(metadata, 'processor_version') or not metadata.processor_version:
            self.validation_errors.append("Processing metadata missing processor_version")
        
        if not hasattr(metadata, 'processing_duration') or metadata.processing_duration is None:
            self.validation_errors.append("Processing metadata missing processing_duration")
    
    def _validate_text_outputs(self, output: StandardizedDocumentOutput):
        """Validate text outputs."""
        if not isinstance(output.plain_text, str):
            self.validation_errors.append("plain_text must be a string")
        
        if not isinstance(output.markdown_text, str):
            self.validation_errors.append("markdown_text must be a string")
        
        # Check that text outputs are not empty if we have content elements
        if output.content_elements and len(output.content_elements) > 0:
            if not output.plain_text.strip():
                self.validation_warnings.append("plain_text is empty despite having content elements")
            
            if not output.markdown_text.strip():
                self.validation_warnings.append("markdown_text is empty despite having content elements")
    
    def _validate_consistency(self, output: StandardizedDocumentOutput):
        """Validate consistency between different parts of the output."""
        # Check element count consistency
        if output.document_structure and output.content_elements:
            actual_count = len(output.content_elements)
            reported_count = output.document_structure.total_elements
            
            if actual_count != reported_count:
                self.validation_warnings.append(
                    f"Element count mismatch: structure reports {reported_count} but found {actual_count}"
                )
        
        # Check table consistency
        if output.document_structure and output.tables:
            has_tables_reported = output.document_structure.has_tables
            has_tables_actual = len(output.tables) > 0
            
            if has_tables_reported != has_tables_actual:
                self.validation_warnings.append(
                    f"Table presence mismatch: structure reports {has_tables_reported} but found {has_tables_actual}"
                )
        
        # Check image consistency
        if output.document_structure and output.images:
            has_images_reported = output.document_structure.has_images
            has_images_actual = len(output.images) > 0
            
            if has_images_reported != has_images_actual:
                self.validation_warnings.append(
                    f"Image presence mismatch: structure reports {has_images_reported} but found {has_images_actual}"
                )
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get a detailed validation report."""
        return {
            "validation_passed": len(self.validation_errors) == 0,
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class OutputFormatStandardizer:
    """Standardizes processor outputs to ensure uniform formatting."""
    
    def __init__(self):
        """Initialize the output format standardizer."""
        self.standardization_log = []
    
    def standardize_output(self, output: StandardizedDocumentOutput) -> StandardizedDocumentOutput:
        """
        Standardize a document output to ensure uniform formatting.
        
        Args:
            output: The output to standardize
            
        Returns:
            Standardized output
        """
        self.standardization_log = []
        
        try:
            # Standardize content elements
            output.content_elements = self._standardize_content_elements(output.content_elements)
            
            # Standardize tables
            output.tables = self._standardize_tables(output.tables)
            
            # Standardize images
            output.images = self._standardize_images(output.images)
            
            # Standardize text outputs
            output.plain_text = self._standardize_plain_text(output.plain_text)
            output.markdown_text = self._standardize_markdown_text(output.markdown_text)
            
            # Ensure processing status is standardized
            if hasattr(output.processing_status, 'value'):
                # It's an enum, keep as is
                pass
            else:
                # It's a string, try to convert to enum
                if output.processing_status == "success":
                    output.processing_status = ProcessingStatus.SUCCESS
                elif output.processing_status == "error":
                    output.processing_status = ProcessingStatus.ERROR
                elif output.processing_status == "partial":
                    output.processing_status = ProcessingStatus.PARTIAL_SUCCESS
            
            logger.info(f"Output standardization completed with {len(self.standardization_log)} modifications")
            
            return output
            
        except Exception as e:
            logger.error(f"Output standardization failed: {e}")
            return output
    
    def _standardize_content_elements(self, elements: List[ContentElement]) -> List[ContentElement]:
        """Standardize content elements."""
        if not elements:
            return elements
        
        standardized = []
        for element in elements:
            # Ensure content is stripped of extra whitespace
            if hasattr(element, 'content') and element.content:
                original_content = element.content
                element.content = element.content.strip()
                if original_content != element.content:
                    self.standardization_log.append(f"Trimmed whitespace from element {element.element_id}")
            
            # Ensure element_id is present
            if not hasattr(element, 'element_id') or not element.element_id:
                element.element_id = f"element_{len(standardized) + 1}"
                self.standardization_log.append(f"Generated element_id: {element.element_id}")
            
            standardized.append(element)
        
        return standardized
    
    def _standardize_tables(self, tables: List[TableData]) -> List[TableData]:
        """Standardize table data."""
        if not tables:
            return tables
        
        standardized = []
        for i, table in enumerate(tables):
            # Ensure headers are strings
            if hasattr(table, 'headers') and table.headers:
                table.headers = [str(header).strip() for header in table.headers]
            
            # Ensure rows are consistent
            if hasattr(table, 'rows') and table.rows:
                standardized_rows = []
                for row in table.rows:
                    standardized_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    standardized_rows.append(standardized_row)
                table.rows = standardized_rows
            
            # Ensure table has metadata
            if not hasattr(table, 'metadata') or not table.metadata:
                table.metadata = {"table_id": f"table_{i+1}"}
                self.standardization_log.append(f"Added metadata to table {i+1}")
            
            standardized.append(table)
        
        return standardized
    
    def _standardize_images(self, images: List[ImageData]) -> List[ImageData]:
        """Standardize image data."""
        if not images:
            return images
        
        standardized = []
        for i, image in enumerate(images):
            # Ensure image_id is present
            if not hasattr(image, 'image_id') or not image.image_id:
                image.image_id = f"image_{i+1}"
                self.standardization_log.append(f"Generated image_id: {image.image_id}")
            
            # Ensure alt_text is present
            if not hasattr(image, 'alt_text') or not image.alt_text:
                image.alt_text = f"Image {image.image_id}"
                self.standardization_log.append(f"Generated alt_text for {image.image_id}")
            
            standardized.append(image)
        
        return standardized
    
    def _standardize_plain_text(self, text: str) -> str:
        """Standardize plain text output."""
        if not text:
            return ""
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line.rstrip()  # Remove trailing whitespace
            cleaned_lines.append(cleaned_line)
        
        # Remove excessive empty lines (more than 2 consecutive)
        result_lines = []
        empty_count = 0
        
        for line in cleaned_lines:
            if line.strip() == "":
                empty_count += 1
                if empty_count <= 2:  # Allow up to 2 consecutive empty lines
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _standardize_markdown_text(self, text: str) -> str:
        """Standardize markdown text output."""
        if not text:
            return ""
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Ensure proper spacing around headers
        lines = text.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            # Add line
            result_lines.append(line.rstrip())
            
            # Add spacing after headers
            if line.startswith('#') and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('#'):
                    # Ensure there's a blank line after header
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        result_lines.append("")
        
        return '\n'.join(result_lines)
    
    def get_standardization_log(self) -> List[str]:
        """Get the standardization log."""
        return self.standardization_log.copy()


class FormatConverter:
    """Utilities for converting between different output formats."""
    
    def __init__(self):
        """Initialize the format converter."""
        self.conversion_log = []
    
    def convert_to_json(self, output: StandardizedDocumentOutput) -> str:
        """Convert standardized output to JSON format."""
        try:
            # Convert to dictionary with proper serialization
            output_dict = output.model_dump()
            
            # Handle datetime serialization
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            json_str = json.dumps(output_dict, indent=2, default=serialize_datetime, ensure_ascii=False)
            self.conversion_log.append("Converted to JSON format")
            return json_str
            
        except Exception as e:
            logger.error(f"Error converting to JSON: {e}")
            raise
    
    def convert_to_html(self, output: StandardizedDocumentOutput) -> str:
        """Convert standardized output to HTML format."""
        try:
            html_parts = ["<!DOCTYPE html>", "<html>", "<head>", 
                         f"<title>{output.document_metadata.get('title', 'Document')}</title>",
                         "</head>", "<body>"]
            
            # Add content elements
            for element in output.content_elements:
                if element.content_type == ContentType.HEADING:
                    level = element.metadata.get("level", 1)
                    html_parts.append(f"<h{level}>{element.content}</h{level}>")
                elif element.content_type == ContentType.PARAGRAPH:
                    html_parts.append(f"<p>{element.content}</p>")
                elif element.content_type == ContentType.LIST:
                    html_parts.append(f"<li>{element.content}</li>")
                else:
                    html_parts.append(f"<div>{element.content}</div>")
            
            # Add tables
            for table in output.tables:
                html_parts.append("<table border='1'>")
                if table.headers:
                    html_parts.append("<thead><tr>")
                    for header in table.headers:
                        html_parts.append(f"<th>{header}</th>")
                    html_parts.append("</tr></thead>")
                
                html_parts.append("<tbody>")
                for row in table.rows:
                    html_parts.append("<tr>")
                    for cell in row:
                        html_parts.append(f"<td>{cell}</td>")
                    html_parts.append("</tr>")
                html_parts.append("</tbody></table>")
            
            # Add images
            for image in output.images:
                alt_text = image.alt_text or f"Image {image.image_id}"
                if image.file_path:
                    html_parts.append(f"<img src='{image.file_path}' alt='{alt_text}' />")
                if image.caption:
                    html_parts.append(f"<p><em>{image.caption}</em></p>")
            
            html_parts.extend(["</body>", "</html>"])
            
            html_str = "\n".join(html_parts)
            self.conversion_log.append("Converted to HTML format")
            return html_str
            
        except Exception as e:
            logger.error(f"Error converting to HTML: {e}")
            raise
    
    def convert_to_xml(self, output: StandardizedDocumentOutput) -> str:
        """Convert standardized output to XML format."""
        try:
            xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<document>"]
            
            # Add metadata
            xml_parts.append("<metadata>")
            for key, value in output.document_metadata.items():
                xml_parts.append(f"<{key}>{value}</{key}>")
            xml_parts.append("</metadata>")
            
            # Add content elements
            xml_parts.append("<content>")
            for element in output.content_elements:
                xml_parts.append(f"<element id='{element.element_id}' type='{element.content_type.value}'>")
                xml_parts.append(f"<text>{element.content}</text>")
                if element.metadata:
                    xml_parts.append("<element_metadata>")
                    for key, value in element.metadata.items():
                        xml_parts.append(f"<{key}>{value}</{key}>")
                    xml_parts.append("</element_metadata>")
                xml_parts.append("</element>")
            xml_parts.append("</content>")
            
            # Add tables
            if output.tables:
                xml_parts.append("<tables>")
                for i, table in enumerate(output.tables):
                    xml_parts.append(f"<table id='table_{i+1}'>")
                    if table.headers:
                        xml_parts.append("<headers>")
                        for header in table.headers:
                            xml_parts.append(f"<header>{header}</header>")
                        xml_parts.append("</headers>")
                    
                    xml_parts.append("<rows>")
                    for row in table.rows:
                        xml_parts.append("<row>")
                        for cell in row:
                            xml_parts.append(f"<cell>{cell}</cell>")
                        xml_parts.append("</row>")
                    xml_parts.append("</rows>")
                    xml_parts.append("</table>")
                xml_parts.append("</tables>")
            
            xml_parts.append("</document>")
            
            xml_str = "\n".join(xml_parts)
            self.conversion_log.append("Converted to XML format")
            return xml_str
            
        except Exception as e:
            logger.error(f"Error converting to XML: {e}")
            raise
    
    def get_conversion_log(self) -> List[str]:
        """Get the conversion log."""
        return self.conversion_log.copy()


class QualityAssuranceChecker:
    """Quality assurance checks for format consistency."""
    
    def __init__(self):
        """Initialize the QA checker."""
        self.qa_issues = []
        self.qa_metrics = {}
    
    def check_format_consistency(self, outputs: List[StandardizedDocumentOutput]) -> Dict[str, Any]:
        """
        Check format consistency across multiple processor outputs.
        
        Args:
            outputs: List of outputs from different processors
            
        Returns:
            Consistency report
        """
        self.qa_issues = []
        self.qa_metrics = {}
        
        if len(outputs) < 2:
            return {
                "consistent": True,
                "issues": [],
                "metrics": {},
                "message": "Need at least 2 outputs to compare consistency"
            }
        
        # Check schema consistency
        self._check_schema_consistency(outputs)
        
        # Check content structure consistency
        self._check_content_structure_consistency(outputs)
        
        # Check text format consistency
        self._check_text_format_consistency(outputs)
        
        # Check metadata consistency
        self._check_metadata_consistency(outputs)
        
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score()
        
        return {
            "consistent": len(self.qa_issues) == 0,
            "consistency_score": consistency_score,
            "issues": self.qa_issues,
            "metrics": self.qa_metrics,
            "total_outputs_compared": len(outputs)
        }
    
    def _check_schema_consistency(self, outputs: List[StandardizedDocumentOutput]):
        """Check that all outputs follow the same schema structure."""
        required_fields = [
            "content_elements", "tables", "images", "document_metadata",
            "document_structure", "processing_metadata", "processing_status",
            "plain_text", "markdown_text"
        ]
        
        for i, output in enumerate(outputs):
            for field in required_fields:
                if not hasattr(output, field):
                    self.qa_issues.append(f"Output {i} missing required field: {field}")
        
        # Check field types consistency
        if len(outputs) >= 2:
            base_output = outputs[0]
            for i, output in enumerate(outputs[1:], 1):
                for field in required_fields:
                    if hasattr(base_output, field) and hasattr(output, field):
                        base_type = type(getattr(base_output, field))
                        current_type = type(getattr(output, field))
                        if base_type != current_type:
                            self.qa_issues.append(
                                f"Field type mismatch in output {i}: {field} "
                                f"(expected {base_type.__name__}, got {current_type.__name__})"
                            )
    
    def _check_content_structure_consistency(self, outputs: List[StandardizedDocumentOutput]):
        """Check content structure consistency."""
        element_counts = []
        table_counts = []
        image_counts = []
        
        for output in outputs:
            element_counts.append(len(output.content_elements))
            table_counts.append(len(output.tables))
            image_counts.append(len(output.images))
        
        # Check if element counts are reasonably similar (within 20% variance)
        if len(set(element_counts)) > 1:
            max_elements = max(element_counts)
            min_elements = min(element_counts)
            if max_elements > 0 and (max_elements - min_elements) / max_elements > 0.2:
                self.qa_issues.append(
                    f"Significant variance in content element counts: {element_counts}"
                )
        
        self.qa_metrics["element_counts"] = element_counts
        self.qa_metrics["table_counts"] = table_counts
        self.qa_metrics["image_counts"] = image_counts
    
    def _check_text_format_consistency(self, outputs: List[StandardizedDocumentOutput]):
        """Check text format consistency."""
        plain_text_lengths = []
        markdown_text_lengths = []
        
        for output in outputs:
            plain_text_lengths.append(len(output.plain_text))
            markdown_text_lengths.append(len(output.markdown_text))
        
        # Check for significant length differences
        if len(set(plain_text_lengths)) > 1:
            max_length = max(plain_text_lengths)
            min_length = min(plain_text_lengths)
            if max_length > 0 and (max_length - min_length) / max_length > 0.3:
                self.qa_issues.append(
                    f"Significant variance in plain text lengths: {plain_text_lengths}"
                )
        
        # Check line ending consistency
        line_ending_types = set()
        for output in outputs:
            if '\r\n' in output.plain_text:
                line_ending_types.add('CRLF')
            elif '\r' in output.plain_text:
                line_ending_types.add('CR')
            elif '\n' in output.plain_text:
                line_ending_types.add('LF')
        
        if len(line_ending_types) > 1:
            self.qa_issues.append(f"Inconsistent line endings: {line_ending_types}")
        
        self.qa_metrics["plain_text_lengths"] = plain_text_lengths
        self.qa_metrics["markdown_text_lengths"] = markdown_text_lengths
        self.qa_metrics["line_ending_types"] = list(line_ending_types)
    
    def _check_metadata_consistency(self, outputs: List[StandardizedDocumentOutput]):
        """Check metadata consistency."""
        processor_names = []
        processing_statuses = []
        
        for output in outputs:
            processor_names.append(output.processing_metadata.processor_name)
            processing_statuses.append(output.processing_status.value if hasattr(output.processing_status, 'value') else str(output.processing_status))
        
        # All should have successful processing status for consistency check
        unique_statuses = set(processing_statuses)
        if len(unique_statuses) > 1:
            self.qa_issues.append(f"Inconsistent processing statuses: {unique_statuses}")
        
        self.qa_metrics["processor_names"] = processor_names
        self.qa_metrics["processing_statuses"] = processing_statuses
    
    def _calculate_consistency_score(self) -> float:
        """Calculate overall consistency score (0-1)."""
        if not self.qa_issues:
            return 1.0
        
        # Deduct points for each issue type
        score = 1.0
        issue_penalty = 0.1  # 10% penalty per issue
        
        score -= len(self.qa_issues) * issue_penalty
        
        return max(0.0, score)
    
    def generate_content_hash(self, output: StandardizedDocumentOutput) -> str:
        """Generate a hash of the content for comparison."""
        # Create a normalized representation for hashing
        content_parts = []
        
        # Add content elements
        for element in sorted(output.content_elements, key=lambda x: x.element_id):
            content_parts.append(f"{element.content_type.value}:{element.content}")
        
        # Add tables
        for table in output.tables:
            table_str = "|".join(table.headers) + "||" + "||".join("|".join(row) for row in table.rows)
            content_parts.append(f"table:{table_str}")
        
        # Add images
        for image in output.images:
            content_parts.append(f"image:{image.image_id}:{image.alt_text or ''}")
        
        # Create hash
        content_string = "||".join(content_parts)
        return hashlib.sha256(content_string.encode('utf-8')).hexdigest()


def validate_and_standardize_output(output: StandardizedDocumentOutput) -> tuple[bool, StandardizedDocumentOutput, Dict[str, Any]]:
    """
    Validate and standardize a document output.
    
    Args:
        output: The output to validate and standardize
        
    Returns:
        Tuple of (is_valid, standardized_output, validation_report)
    """
    # First standardize
    standardizer = OutputFormatStandardizer()
    standardized_output = standardizer.standardize_output(output)
    
    # Then validate
    validator = OutputFormatValidator()
    is_valid = validator.validate_output(standardized_output)
    validation_report = validator.get_validation_report()
    
    # Add standardization info to report
    validation_report["standardization_log"] = standardizer.get_standardization_log()
    
    return is_valid, standardized_output, validation_report


def compare_processor_outputs(outputs: List[StandardizedDocumentOutput]) -> Dict[str, Any]:
    """
    Compare outputs from different processors for consistency.
    
    Args:
        outputs: List of outputs from different processors
        
    Returns:
        Comparison report
    """
    qa_checker = QualityAssuranceChecker()
    return qa_checker.check_format_consistency(outputs)


def convert_output_format(output: StandardizedDocumentOutput, target_format: str) -> str:
    """
    Convert standardized output to different formats.
    
    Args:
        output: The output to convert
        target_format: Target format ('json', 'html', 'xml')
        
    Returns:
        Converted output as string
        
    Raises:
        ValueError: If target format is not supported
    """
    converter = FormatConverter()
    
    if target_format.lower() == 'json':
        return converter.convert_to_json(output)
    elif target_format.lower() == 'html':
        return converter.convert_to_html(output)
    elif target_format.lower() == 'xml':
        return converter.convert_to_xml(output)
    else:
        raise ValueError(f"Unsupported target format: {target_format}. Supported formats: json, html, xml")