"""Independent system validation and testing framework."""

import os
import sys
import time
import json
import logging
import subprocess
import threading
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import concurrent.futures
import psutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

logger = logging.getLogger(__name__)


class SystemValidator:
    """Independent system validation framework."""
    
    def __init__(self):
        """Initialize system validator."""
        self.test_results = {}
        self.performance_metrics = {}
        self.error_log = []
        self.start_time = None
        self.end_time = None
        
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive system validation."""
        self.start_time = datetime.now(timezone.utc)
        logger.info("Starting comprehensive system validation")
        
        validation_results = {
            'validation_id': f"validation_{int(time.time())}",
            'start_time': self.start_time.isoformat(),
            'test_environment': self._get_test_environment(),
            'test_results': {},
            'performance_metrics': {},
            'error_analysis': {},
            'system_health': {},
            'recommendations': []
        }
        
        try:
            # 1. Run all test suites
            validation_results['test_results'] = self._run_all_test_suites()
            
            # 2. Test document lifecycle
            validation_results['document_lifecycle'] = self._test_document_lifecycle()
            
            # 3. Performance and scalability testing
            validation_results['performance_metrics'] = self._test_performance_scalability()
            
            # 4. Concurrent processing tests
            validation_results['concurrency_tests'] = self._test_concurrent_processing()
            
            # 5. Error handling and recovery tests
            validation_results['error_handling'] = self._test_error_handling_recovery()
            
            # 6. System stability tests
            validation_results['stability_tests'] = self._test_system_stability()
            
            # 7. Resource utilization analysis
            validation_results['resource_analysis'] = self._analyze_resource_utilization()
            
            # 8. Generate system health assessment
            validation_results['system_health'] = self._assess_system_health(validation_results)
            
            # 9. Generate recommendations
            validation_results['recommendations'] = self._generate_recommendations(validation_results)
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_results['fatal_error'] = str(e)
        
        finally:
            self.end_time = datetime.now(timezone.utc)
            validation_results['end_time'] = self.end_time.isoformat()
            validation_results['total_duration'] = (self.end_time - self.start_time).total_seconds()
        
        return validation_results   
 
    def _get_test_environment(self) -> Dict[str, Any]:
        """Get test environment information."""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': os.getcwd(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_free': psutil.disk_usage('.').free
            }
        }
    
    def _run_all_test_suites(self) -> Dict[str, Any]:
        """Run all test suites independently."""
        test_results = {
            'unit_tests': self._run_unit_tests(),
            'integration_tests': self._run_integration_tests(),
            'system_tests': self._run_system_tests()
        }
        
        # Calculate overall test metrics
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for suite_name, suite_results in test_results.items():
            if isinstance(suite_results, dict) and 'summary' in suite_results:
                summary = suite_results['summary']
                total_tests += summary.get('total', 0)
                total_passed += summary.get('passed', 0)
                total_failed += summary.get('failed', 0)
        
        test_results['overall_summary'] = {
            'total_tests': total_tests,
            'passed': total_passed,
            'failed': total_failed,
            'pass_rate': total_passed / total_tests if total_tests > 0 else 0.0
        }
        
        return test_results
    
    def _run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests independently."""
        try:
            start_time = time.time()
            
            # Run pytest on unit tests
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                'tests/unit/', 
                '-v', '--tb=short', '--json-report', '--json-report-file=/tmp/unit_test_report.json'
            ], capture_output=True, text=True, timeout=300)
            
            duration = time.time() - start_time
            
            # Parse results
            test_summary = self._parse_pytest_output(result.stdout, result.stderr)
            
            return {
                'duration': duration,
                'return_code': result.returncode,
                'summary': test_summary,
                'stdout': result.stdout[-2000:],  # Last 2000 chars
                'stderr': result.stderr[-1000:] if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            return {
                'duration': 300,
                'return_code': -1,
                'error': 'Unit tests timed out after 5 minutes',
                'summary': {'total': 0, 'passed': 0, 'failed': 0}
            }
        except Exception as e:
            return {
                'duration': 0,
                'return_code': -1,
                'error': str(e),
                'summary': {'total': 0, 'passed': 0, 'failed': 0}
            }
    
    def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests independently."""
        try:
            start_time = time.time()
            
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                'tests/integration/', 
                '-v', '--tb=short'
            ], capture_output=True, text=True, timeout=600)
            
            duration = time.time() - start_time
            
            test_summary = self._parse_pytest_output(result.stdout, result.stderr)
            
            return {
                'duration': duration,
                'return_code': result.returncode,
                'summary': test_summary,
                'stdout': result.stdout[-2000:],
                'stderr': result.stderr[-1000:] if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            return {
                'duration': 600,
                'return_code': -1,
                'error': 'Integration tests timed out after 10 minutes',
                'summary': {'total': 0, 'passed': 0, 'failed': 0}
            }
        except Exception as e:
            return {
                'duration': 0,
                'return_code': -1,
                'error': str(e),
                'summary': {'total': 0, 'passed': 0, 'failed': 0}
            }
    
    def _run_system_tests(self) -> Dict[str, Any]:
        """Run system tests independently."""
        try:
            start_time = time.time()
            
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                'tests/system/', 
                '-v', '--tb=short'
            ], capture_output=True, text=True, timeout=900)
            
            duration = time.time() - start_time
            
            test_summary = self._parse_pytest_output(result.stdout, result.stderr)
            
            return {
                'duration': duration,
                'return_code': result.returncode,
                'summary': test_summary,
                'stdout': result.stdout[-2000:],
                'stderr': result.stderr[-1000:] if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            return {
                'duration': 900,
                'return_code': -1,
                'error': 'System tests timed out after 15 minutes',
                'summary': {'total': 0, 'passed': 0, 'failed': 0}
            }
        except Exception as e:
            return {
                'duration': 0,
                'return_code': -1,
                'error': str(e),
                'summary': {'total': 0, 'passed': 0, 'failed': 0}
            }