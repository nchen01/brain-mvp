"""Format utilities for document processing consistency and validation."""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
import json

from .schemas import StandardizedDocumentOutput, ContentType, ProcessingStatus
from .output_validator import (
    validate_and_standardize_output,
    compare_processor_outputs,
    convert_output_format
)

logger = logging.getLogger(__name__)


class FormatConsistencyManager:
    """Manages format consistency across different processors and documents."""
    
    def __init__(self):
        """Initialize the format consistency manager."""
        self.consistency_reports = []
        self.format_standards = self._load_format_standards()
    
    def _load_format_standards(self) -> Dict[str, Any]:
        """Load format standards and requirements."""
        return {
            "required_fields": [
                "content_elements", "tables", "images", "document_metadata",
                "document_structure", "processing_metadata", "processing_status",
                "plain_text", "markdown_text"
            ],
            "content_type_standards": {
                "heading": {"required_metadata": ["level"], "max_level": 6},
                "paragraph": {"min_length": 1, "max_length": 10000},
                "table": {"required_fields": ["headers", "rows"]},
                "image": {"required_fields": ["image_id"]},
                "list": {"min_items": 1}
            },
            "text_standards": {
                "plain_text": {"encoding": "utf-8", "line_endings": "\\n"},
                "markdown_text": {"encoding": "utf-8", "line_endings": "\\n"}
            },
            "quality_thresholds": {
                "min_consistency_score": 0.8,
                "max_validation_errors": 0,
                "max_validation_warnings": 5
            }
        }
    
    def validate_output_against_standards(self, output: StandardizedDocumentOutput) -> Dict[str, Any]:
        """
        Validate output against format standards.
        
        Args:
            output: The output to validate
            
        Returns:
            Validation report with standards compliance
        """
        is_valid, standardized_output, validation_report = validate_and_standardize_output(output)
        
        # Additional standards validation
        standards_report = self._check_standards_compliance(standardized_output)
        
        # Combine reports
        combined_report = {
            "basic_validation": validation_report,
            "standards_compliance": standards_report,
            "overall_valid": is_valid and standards_report["compliant"],
            "standardized_output": standardized_output
        }
        
        return combined_report
    
    def _check_standards_compliance(self, output: StandardizedDocumentOutput) -> Dict[str, Any]:
        """Check compliance with format standards."""
        compliance_issues = []
        compliance_score = 1.0
        
        # Check content type standards
        for element in output.content_elements:
            content_type = element.content_type
            if content_type in self.format_standards["content_type_standards"]:
                standards = self.format_standards["content_type_standards"][content_type]
                
                # Check required metadata
                if "required_metadata" in standards:
                    for required_field in standards["required_metadata"]:
                        if required_field not in element.metadata:
                            compliance_issues.append(
                                f"Element {element.element_id} missing required metadata: {required_field}"
                            )
                            compliance_score -= 0.1
                
                # Check specific standards
                if content_type == "heading" and "level" in element.metadata:
                    level = element.metadata["level"]
                    max_level = standards.get("max_level", 6)
                    if level > max_level:
                        compliance_issues.append(
                            f"Heading {element.element_id} level {level} exceeds maximum {max_level}"
                        )
                        compliance_score -= 0.05
                
                elif content_type == "paragraph":
                    content_length = len(element.content)
                    min_length = standards.get("min_length", 1)
                    max_length = standards.get("max_length", 10000)
                    
                    if content_length < min_length:
                        compliance_issues.append(
                            f"Paragraph {element.element_id} too short: {content_length} < {min_length}"
                        )
                        compliance_score -= 0.02
                    
                    elif content_length > max_length:
                        compliance_issues.append(
                            f"Paragraph {element.element_id} too long: {content_length} > {max_length}"
                        )
                        compliance_score -= 0.02
        
        # Ensure score doesn't go below 0
        compliance_score = max(0.0, compliance_score)
        
        return {
            "compliant": len(compliance_issues) == 0,
            "compliance_score": compliance_score,
            "issues": compliance_issues,
            "standards_version": "1.0"
        }
    
    def batch_validate_outputs(self, outputs: List[StandardizedDocumentOutput]) -> Dict[str, Any]:
        """Validate multiple outputs and check consistency."""
        individual_reports = []
        all_valid = True
        
        # Validate each output individually
        for i, output in enumerate(outputs):
            report = self.validate_output_against_standards(output)
            report["output_index"] = i
            individual_reports.append(report)
            
            if not report["overall_valid"]:
                all_valid = False
        
        # Check consistency across outputs
        consistency_report = compare_processor_outputs(outputs)
        
        # Calculate overall batch score
        individual_scores = [r["standards_compliance"]["compliance_score"] for r in individual_reports]
        avg_individual_score = sum(individual_scores) / len(individual_scores) if individual_scores else 0
        consistency_score = consistency_report.get("consistency_score", 0)
        
        overall_score = (avg_individual_score + consistency_score) / 2
        
        return {
            "batch_valid": all_valid and consistency_report["consistent"],
            "overall_score": overall_score,
            "individual_reports": individual_reports,
            "consistency_report": consistency_report,
            "total_outputs": len(outputs),
            "valid_outputs": sum(1 for r in individual_reports if r["overall_valid"])
        }
    
    def generate_format_report(self, outputs: List[StandardizedDocumentOutput], output_file: Optional[str] = None) -> Dict[str, Any]:
        """Generate a comprehensive format report."""
        batch_report = self.batch_validate_outputs(outputs)
        
        # Add summary statistics
        summary = {
            "total_outputs_processed": len(outputs),
            "validation_success_rate": batch_report["valid_outputs"] / len(outputs) if outputs else 0,
            "overall_quality_score": batch_report["overall_score"],
            "consistency_achieved": batch_report["consistency_report"]["consistent"],
            "recommendations": self._generate_recommendations(batch_report)
        }
        
        comprehensive_report = {
            "summary": summary,
            "detailed_results": batch_report,
            "format_standards_version": "1.0",
            "report_timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }
        
        # Save to file if requested
        if output_file:
            self._save_report(comprehensive_report, output_file)
        
        return comprehensive_report
    
    def _generate_recommendations(self, batch_report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Check overall score
        overall_score = batch_report["overall_score"]
        if overall_score < 0.8:
            recommendations.append("Overall format quality is below recommended threshold (0.8). Review processor configurations.")
        
        # Check consistency
        if not batch_report["consistency_report"]["consistent"]:
            recommendations.append("Output formats are inconsistent across processors. Review standardization logic.")
        
        return recommendations
    
    def _save_report(self, report: Dict[str, Any], output_file: str):
        """Save report to file."""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Format report saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save format report: {e}")


class OutputFormatConverter:
    """Utility for converting outputs to different formats with validation."""
    
    def __init__(self):
        """Initialize the format converter."""
        self.supported_formats = ['json', 'html', 'xml', 'markdown', 'plain_text']
    
    def convert_with_validation(self, output: StandardizedDocumentOutput, target_format: str) -> Tuple[str, Dict[str, Any]]:
        """Convert output to target format with validation."""
        # First validate and standardize
        is_valid, standardized_output, validation_report = validate_and_standardize_output(output)
        
        if not is_valid:
            logger.warning(f"Converting output with validation errors: {validation_report.get('errors', [])}")
        
        # Convert to target format
        if target_format.lower() in ['json', 'html', 'xml']:
            converted = convert_output_format(standardized_output, target_format)
        elif target_format.lower() == 'markdown':
            converted = standardized_output.markdown_text
        elif target_format.lower() == 'plain_text':
            converted = standardized_output.plain_text
        else:
            raise ValueError(f"Unsupported format: {target_format}. Supported: {self.supported_formats}")
        
        return converted, validation_report
    
    def batch_convert(self, outputs: List[StandardizedDocumentOutput], target_format: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Convert multiple outputs to target format."""
        results = []
        
        for output in outputs:
            try:
                converted, report = self.convert_with_validation(output, target_format)
                results.append((converted, report))
            except Exception as e:
                error_report = {
                    "validation_passed": False,
                    "errors": [f"Conversion failed: {str(e)}"],
                    "warnings": []
                }
                results.append(("", error_report))
        
        return results


def create_format_consistency_report(outputs: List[StandardizedDocumentOutput], output_file: Optional[str] = None) -> Dict[str, Any]:
    """Create a comprehensive format consistency report."""
    manager = FormatConsistencyManager()
    return manager.generate_format_report(outputs, output_file)


def validate_processor_output_quality(output: StandardizedDocumentOutput) -> Dict[str, Any]:
    """Validate the quality of a single processor output."""
    manager = FormatConsistencyManager()
    return manager.validate_output_against_standards(output)


def ensure_format_consistency(outputs: List[StandardizedDocumentOutput]) -> List[StandardizedDocumentOutput]:
    """Ensure format consistency across multiple outputs."""
    standardized_outputs = []
    
    for output in outputs:
        is_valid, standardized_output, _ = validate_and_standardize_output(output)
        standardized_outputs.append(standardized_output)
    
    return standardized_outputs