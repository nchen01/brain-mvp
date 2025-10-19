#!/usr/bin/env python3
"""Test runner script with dependency checking."""

import sys
import subprocess
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.dependency_checker import check_test_dependencies, dependency_checker


def install_dependencies(missing_deps: list, package_manager: str = "pip") -> bool:
    """
    Install missing dependencies.
    
    Args:
        missing_deps: List of missing dependency packages
        package_manager: Package manager to use ('pip' or 'uv')
    
    Returns:
        True if installation successful, False otherwise
    """
    if not missing_deps:
        return True
    
    print(f"Installing missing dependencies with {package_manager}...")
    
    try:
        if package_manager == "uv":
            cmd = ["uv", "add"] + missing_deps
        else:
            cmd = ["pip", "install"] + missing_deps
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Successfully installed dependencies")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ {package_manager} not found. Please install it first.")
        return False


def run_tests(test_path: str = None, verbose: bool = True, install_deps: bool = False) -> int:
    """
    Run tests with dependency checking.
    
    Args:
        test_path: Specific test path to run
        verbose: Whether to run tests in verbose mode
        install_deps: Whether to automatically install missing dependencies
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    print("🔍 Checking test dependencies...")
    
    # Check dependencies
    test_available, missing_deps = check_test_dependencies()
    
    if not test_available:
        print(f"\n❌ Missing dependencies detected:")
        for dep in missing_deps:
            print(f"   - {dep}")
        
        if install_deps:
            print(f"\n📦 Attempting to install missing dependencies...")
            if not install_dependencies(missing_deps):
                return 1
            
            # Re-check after installation
            test_available, missing_deps = check_test_dependencies()
            if not test_available:
                print(f"❌ Some dependencies still missing after installation")
                return 1
        else:
            print(f"\n💡 To install missing dependencies, run:")
            print(f"   pip install {' '.join(missing_deps)}")
            print(f"   or: uv add {' '.join(missing_deps)}")
            print(f"\n   Or run this script with --install-deps flag")
            return 1
    
    print("✅ All test dependencies are available")
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.append("--tb=short")
    
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    print(f"\n🧪 Running tests: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run tests with dependency checking")
    parser.add_argument(
        "test_path", 
        nargs="?", 
        help="Specific test path to run (e.g., tests/integration/test_meta_document_rag_integration.py::TestLightRAGIntegration::test_lightrag_vector_embeddings)"
    )
    parser.add_argument(
        "--install-deps", 
        action="store_true", 
        help="Automatically install missing dependencies"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true", 
        help="Run tests in quiet mode"
    )
    parser.add_argument(
        "--check-only", 
        action="store_true", 
        help="Only check dependencies, don't run tests"
    )
    
    args = parser.parse_args()
    
    if args.check_only:
        print("🔍 Checking dependencies only...")
        test_available, missing_deps = check_test_dependencies()
        dependency_checker.print_dependency_report()
        return 0 if test_available else 1
    
    return run_tests(
        test_path=args.test_path,
        verbose=not args.quiet,
        install_deps=args.install_deps
    )


if __name__ == "__main__":
    sys.exit(main())