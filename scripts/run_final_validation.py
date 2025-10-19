#!/usr/bin/env python3
"""
Final System Validation Runner
Executes comprehensive system testing and generates endtoendv2.md report
"""

import sys
import os
import json
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from tests.system.test_final_validation import FreshSystemValidator


def generate_endtoendv2_report(validation_report: dict) -> str:
    """Generate comprehensive endtoendv2.md report from validation results."""
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    report_content = f"""# DocForge Brain MVP - Final System Validation Report v2.0

**Generated:** {timestamp}  
**Validation Framework:** Fresh System Testing v1.0  
**Test Environment:** Isolated validation environment  

## Executive Summary

### System Health Assessment
- **Overall Status:** {validation_report['overall_assessment']['health_status']}
- **Success Rate:** {validation_report['overall_assessment']['success_rate']}%
- **Production Readiness:** {validation_report['production_readiness']['readiness_level']}
- **Readiness Score:** {validation_report['production_readiness']['readiness_score']}/100

### Test Results Overview
- **Total Tests:** {validation_report['overall_assessment']['total_tests']}
- **Passed:** {validation_report['overall_assessment']['passed_tests']}
- **Failed:** {validation_report['overall_assessment']['failed_tests']}
- **Warnings:** {validation_report['overall_assessment']['warning_tests']}
- **Skipped:** {validation_report['overall_assessment']['skipped_tests']}

## Component Analysis

"""

    # Component details
    for component, summary in validation_report['component_analysis'].items():
        status_emoji = {
            'EXCELLENT': '🟢',
            'GOOD': '🟡',
            'ACCEPTABLE': '🟠',
            'NEEDS_ATTENTION': '🔴'
        }.get(summary['status'], '⚪')
        
        report_content += f"""### {status_emoji} {component}
- **Status:** {summary['status']}
- **Tests:** {summary['passed']}/{summary['total_tests']} passed
- **Failures:** {summary['failed']}
- **Warnings:** {summary['warnings']}
- **Avg Execution Time:** {summary['avg_execution_time']:.3f}s

"""

    # Detailed test results
    report_content += """## Detailed Test Results

"""

    for result in validation_report['detailed_results']:
        status_emoji = {
            'PASS': '✅',
            'FAIL': '❌',
            'WARN': '⚠️',
            'SKIP': '⏭️'
        }.get(result['status'], '❓')
        
        report_content += f"""### {status_emoji} {result['component']}.{result['test_name']}
- **Status:** {result['status']}
- **Execution Time:** {result['execution_time']:.3f}s
- **Message:** {result['message']}

"""
        
        if result.get('details'):
            report_content += "**Details:**\n"
            for key, value in result['details'].items():
                if isinstance(value, (list, dict)):
                    report_content += f"- {key}: {len(value) if isinstance(value, list) else 'complex object'}\n"
                else:
                    report_content += f"- {key}: {value}\n"
            report_content += "\n"
        
        if result.get('error_trace'):
            report_content += f"""**Error Details:**
```
{result['error_trace'][:500]}...
```

"""

    # Performance analysis
    report_content += """## Performance Analysis

### Component Performance
"""
    
    for component, times in validation_report['performance_analysis']['component_times'].items():
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            report_content += f"""- **{component}:** Avg {avg_time:.3f}s (Min: {min_time:.3f}s, Max: {max_time:.3f}s)
"""

    # System capabilities
    report_content += """
## System Capabilities Assessment

### ✅ Working Features
"""

    working_features = []
    for result in validation_report['detailed_results']:
        if result['status'] == 'PASS':
            working_features.append(f"- {result['component']}: {result['test_name']}")
    
    report_content += "\n".join(working_features[:10])  # Top 10 working features
    
    if len(working_features) > 10:
        report_content += f"\n- ... and {len(working_features) - 10} more working features"

    report_content += """

### ❌ Issues Identified
"""

    issues = []
    for result in validation_report['detailed_results']:
        if result['status'] == 'FAIL':
            issues.append(f"- {result['component']}.{result['test_name']}: {result['message']}")
    
    if issues:
        report_content += "\n".join(issues)
    else:
        report_content += "- No critical issues identified"

    report_content += """

### ⚠️ Warnings and Recommendations
"""

    warnings = []
    for result in validation_report['detailed_results']:
        if result['status'] == 'WARN':
            warnings.append(f"- {result['component']}.{result['test_name']}: {result['message']}")
    
    if warnings:
        report_content += "\n".join(warnings)
    else:
        report_content += "- No warnings identified"

    # Recommendations
    report_content += """

## Recommendations

"""
    
    for i, recommendation in enumerate(validation_report['recommendations'], 1):
        report_content += f"{i}. {recommendation}\n"

    # Production readiness
    report_content += f"""
## Production Readiness Assessment

### Readiness Level: {validation_report['production_readiness']['readiness_level']}
### Readiness Score: {validation_report['production_readiness']['readiness_score']}/100

"""

    if validation_report['production_readiness']['blocking_issues']:
        report_content += """### 🚫 Blocking Issues
"""
        for issue in validation_report['production_readiness']['blocking_issues']:
            report_content += f"- {issue}\n"
    else:
        report_content += "### ✅ No Blocking Issues Identified\n"

    # Next steps
    report_content += """
## Next Steps

"""
    
    for i, step in enumerate(validation_report['next_steps'], 1):
        report_content += f"{i}. {step}\n"

    # Technical details
    report_content += f"""
## Technical Validation Details

### Test Environment
- **Environment Path:** {validation_report['validation_metadata']['test_environment']}
- **Execution Duration:** {validation_report['validation_metadata']['execution_duration_seconds']:.2f} seconds
- **Framework Version:** {validation_report['validation_metadata']['validation_framework_version']}

### System Architecture Validation
The validation tested the complete DocForge Brain MVP architecture:

1. **Configuration Management System**
   - Configuration loading and validation
   - Dynamic configuration updates
   - Environment-specific settings

2. **Document Processing Pipeline**
   - Preprocessing (format conversion, validation)
   - Postprocessing (chunking, abbreviation expansion)
   - Storage (document and metadata persistence)

3. **RAG (Retrieval Augmented Generation) System**
   - Document indexing and embedding
   - Query processing and retrieval
   - Integration with LightRAG

4. **Versioning and Lineage Management**
   - Version creation and tracking
   - Document lineage management
   - Version comparison capabilities

5. **Error Handling and Recovery**
   - Graceful error handling
   - System recovery mechanisms
   - Error logging and reporting

6. **Performance and Scalability**
   - Concurrent processing capabilities
   - Resource utilization monitoring
   - Performance benchmarking

### Independent Analysis Summary

This validation was conducted completely independently without referencing previous test results. The system was tested in a fresh, isolated environment to ensure objective assessment of current capabilities.

**Key Findings:**
- System demonstrates {validation_report['overall_assessment']['success_rate']}% reliability across all tested components
- {validation_report['overall_assessment']['passed_tests']} out of {validation_report['overall_assessment']['total_tests']} validation tests passed
- Production readiness assessed at {validation_report['production_readiness']['readiness_score']}/100

**Comparison with Previous Assessments:**
This report (endtoendv2.md) provides a fresh, independent analysis that can be compared with the original endtoend.md to track system improvements and identify any regressions.

---

*This report was generated automatically by the DocForge Brain MVP Final Validation Framework v1.0*
*For technical details, see the complete validation results in the test output.*
"""

    return report_content


def main():
    """Main execution function."""
    print("🚀 Starting DocForge Brain MVP Final System Validation...")
    print("=" * 70)
    
    # Initialize validator
    validator = FreshSystemValidator()
    
    try:
        # Run comprehensive validation
        validation_report = validator.run_comprehensive_validation()
        
        if validation_report:
            # Generate endtoendv2.md report
            print("\n📝 Generating endtoendv2.md report...")
            
            report_content = generate_endtoendv2_report(validation_report)
            
            # Save report
            report_path = Path("endtoendv2.md")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"✅ Report saved to: {report_path.absolute()}")
            
            # Save detailed JSON results
            json_path = Path("validation_results_detailed.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(validation_report, f, indent=2, default=str)
            
            print(f"📊 Detailed results saved to: {json_path.absolute()}")
            
            # Print summary
            print("\n" + "=" * 70)
            print("🎯 FINAL VALIDATION SUMMARY")
            print("=" * 70)
            print(f"Health Status: {validation_report['overall_assessment']['health_status']}")
            print(f"Success Rate: {validation_report['overall_assessment']['success_rate']}%")
            print(f"Production Readiness: {validation_report['production_readiness']['readiness_level']}")
            print(f"Tests Passed: {validation_report['overall_assessment']['passed_tests']}/{validation_report['overall_assessment']['total_tests']}")
            
            if validation_report['production_readiness']['blocking_issues']:
                print("\n🚫 BLOCKING ISSUES:")
                for issue in validation_report['production_readiness']['blocking_issues']:
                    print(f"  - {issue}")
            
            print("\n📋 TOP RECOMMENDATIONS:")
            for i, rec in enumerate(validation_report['recommendations'][:3], 1):
                print(f"  {i}. {rec}")
            
            print(f"\n📄 Full report available in: endtoendv2.md")
            
            return validation_report
        
        else:
            print("❌ Validation failed - no report generated")
            return None
    
    except Exception as e:
        print(f"❌ Fatal error during validation: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()