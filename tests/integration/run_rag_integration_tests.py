#!/usr/bin/env python3
"""
RAG Integration Test Runner

This script runs all RAG-related integration tests and provides
a comprehensive report of the test results.

Usage:
    python tests/integration/run_rag_integration_tests.py [--verbose] [--test-pattern PATTERN]
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def run_test_suite(test_file, verbose=False, pattern=None):
    """Run a specific test suite and return results."""
    print(f"\\n{'='*60}")
    print(f"Running: {test_file}")
    print(f"{'='*60}")
    
    cmd = ["python", "-m", "pytest", test_file]
    
    if verbose:
        cmd.extend(["-v", "-s"])
    
    if pattern:
        cmd.extend(["-k", pattern])
    
    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    except ImportError:
        pass
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per test suite
        )
        
        execution_time = time.time() - start_time
        
        return {
            'test_file': test_file,
            'success': result.returncode == 0,
            'execution_time': execution_time,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            'test_file': test_file,
            'success': False,
            'execution_time': time.time() - start_time,
            'stdout': '',
            'stderr': 'Test suite timed out after 5 minutes',
            'return_code': -1
        }
    except Exception as e:
        return {
            'test_file': test_file,
            'success': False,
            'execution_time': time.time() - start_time,
            'stdout': '',
            'stderr': f'Error running test: {str(e)}',
            'return_code': -2
        }


def extract_test_stats(stdout):
    """Extract test statistics from pytest output."""
    stats = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'warnings': 0
    }
    
    lines = stdout.split('\\n')
    
    for line in lines:
        if 'passed' in line and 'failed' in line:
            # Look for summary line like "5 passed, 2 failed, 1 skipped"
            parts = line.split()
            for i, part in enumerate(parts):
                if part.isdigit() and i + 1 < len(parts):
                    count = int(part)
                    status = parts[i + 1].rstrip(',')
                    if status in stats:
                        stats[status] = count
        elif line.strip().endswith('warnings summary'):
            # Count warnings
            try:
                warning_count = int(line.split()[0])
                stats['warnings'] = warning_count
            except (ValueError, IndexError):
                pass
    
    return stats


def print_test_summary(results):
    """Print a comprehensive test summary."""
    print(f"\\n{'='*80}")
    print("RAG INTEGRATION TEST SUMMARY")
    print(f"{'='*80}")
    
    total_tests = len(results)
    successful_suites = sum(1 for r in results if r['success'])
    failed_suites = total_tests - successful_suites
    total_time = sum(r['execution_time'] for r in results)
    
    print(f"\\nOverall Results:")
    print(f"  Test Suites Run: {total_tests}")
    print(f"  Successful Suites: {successful_suites}")
    print(f"  Failed Suites: {failed_suites}")
    print(f"  Total Execution Time: {total_time:.2f} seconds")
    print(f"  Average Time per Suite: {total_time/total_tests:.2f} seconds")
    
    # Detailed results for each suite
    print(f"\\nDetailed Results:")
    print(f"{'Suite':<40} {'Status':<10} {'Time':<8} {'Tests':<15}")
    print(f"{'-'*80}")
    
    total_stats = {'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 0, 'warnings': 0}
    
    for result in results:
        suite_name = Path(result['test_file']).stem
        status = "PASS" if result['success'] else "FAIL"
        time_str = f"{result['execution_time']:.1f}s"
        
        # Extract test statistics
        stats = extract_test_stats(result['stdout'])
        test_summary = f"{stats['passed']}P/{stats['failed']}F/{stats['skipped']}S"
        
        # Add to totals
        for key in total_stats:
            total_stats[key] += stats[key]
        
        print(f"{suite_name:<40} {status:<10} {time_str:<8} {test_summary:<15}")
        
        # Show errors for failed suites
        if not result['success']:
            print(f"  Error: {result['stderr'][:100]}...")
    
    print(f"{'-'*80}")
    print(f"{'TOTALS':<40} {'':<10} {total_time:.1f}s {total_stats['passed']}P/{total_stats['failed']}F/{total_stats['skipped']}S")
    
    # Show warnings summary
    if total_stats['warnings'] > 0:
        print(f"\\nWarnings: {total_stats['warnings']} warnings detected across all test suites")
    
    # Overall status
    if failed_suites == 0:
        print(f"\\n🎉 ALL RAG INTEGRATION TESTS PASSED! 🎉")
        return True
    else:
        print(f"\\n❌ {failed_suites} test suite(s) failed. See details above.")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")
    
    required_packages = [
        'pytest',
        'sentence-transformers',
        'lightrag',
        'numpy',
        'asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\\nMissing packages: {', '.join(missing_packages)}")
        print("Please install missing packages before running tests.")
        return False
    
    print("All dependencies available.")
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run RAG integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Run tests in verbose mode")
    parser.add_argument("--test-pattern", "-k", type=str,
                       help="Run only tests matching this pattern")
    parser.add_argument("--quick", action="store_true",
                       help="Run only quick tests (skip performance benchmarks)")
    parser.add_argument("--check-deps", action="store_true",
                       help="Only check dependencies, don't run tests")
    
    args = parser.parse_args()
    
    print("RAG Integration Test Runner")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    if args.check_deps:
        print("\\nDependency check complete.")
        sys.exit(0)
    
    # Define test suites to run
    test_suites = [
        "tests/integration/test_meta_document_rag_integration.py",
        "tests/integration/test_vector_embedding_integration.py",
    ]
    
    # Add complete pipeline test unless quick mode
    if not args.quick:
        test_suites.append("tests/integration/test_complete_rag_pipeline.py")
    
    print(f"\\nRunning {len(test_suites)} test suites...")
    if args.quick:
        print("(Quick mode: skipping performance benchmarks)")
    
    # Run all test suites
    results = []
    
    for test_suite in test_suites:
        if not os.path.exists(test_suite):
            print(f"Warning: Test suite not found: {test_suite}")
            continue
        
        result = run_test_suite(test_suite, args.verbose, args.test_pattern)
        results.append(result)
        
        # Print immediate result
        status = "PASS" if result['success'] else "FAIL"
        print(f"Result: {status} ({result['execution_time']:.1f}s)")
        
        # Show errors immediately for failed tests
        if not result['success'] and result['stderr']:
            print(f"Error output:")
            print(result['stderr'][:500])
            if len(result['stderr']) > 500:
                print("... (truncated)")
    
    # Print comprehensive summary
    success = print_test_summary(results)
    
    # Additional recommendations
    print(f"\\nRecommendations:")
    if success:
        print("  • All tests passed! The RAG system is working correctly.")
        print("  • Consider running performance benchmarks if not already done.")
        print("  • Review any warnings that may have been generated.")
    else:
        print("  • Review failed test output above for specific issues.")
        print("  • Check that all required dependencies are properly installed.")
        print("  • Ensure sufficient disk space and memory for test execution.")
        print("  • Consider running tests individually for easier debugging.")
    
    print(f"\\nFor more detailed output, run with --verbose flag.")
    print(f"To run specific tests, use --test-pattern 'pattern_name'")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()