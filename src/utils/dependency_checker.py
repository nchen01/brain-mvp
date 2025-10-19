"""Dependency checker utility for graceful handling of missing dependencies."""

import logging
import importlib
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DependencyChecker:
    """Utility class to check and manage optional dependencies."""
    
    def __init__(self):
        """Initialize the dependency checker."""
        self.checked_dependencies = {}
        self.missing_dependencies = []
        self.available_dependencies = []
    
    def check_dependency(self, module_name: str, package_name: Optional[str] = None) -> bool:
        """
        Check if a dependency is available.
        
        Args:
            module_name: The module name to import (e.g., 'pydantic')
            package_name: The package name for installation (e.g., 'pydantic>=2.5.0')
        
        Returns:
            True if dependency is available, False otherwise
        """
        if module_name in self.checked_dependencies:
            return self.checked_dependencies[module_name]
        
        try:
            importlib.import_module(module_name)
            self.checked_dependencies[module_name] = True
            self.available_dependencies.append(module_name)
            return True
        except ImportError:
            self.checked_dependencies[module_name] = False
            self.missing_dependencies.append({
                'module': module_name,
                'package': package_name or module_name
            })
            return False
    
    def check_multiple_dependencies(self, dependencies: Dict[str, str]) -> Dict[str, bool]:
        """
        Check multiple dependencies at once.
        
        Args:
            dependencies: Dict mapping module names to package names
        
        Returns:
            Dict mapping module names to availability status
        """
        results = {}
        for module_name, package_name in dependencies.items():
            results[module_name] = self.check_dependency(module_name, package_name)
        return results
    
    def get_missing_dependencies(self) -> List[Dict[str, str]]:
        """Get list of missing dependencies."""
        return self.missing_dependencies
    
    def get_available_dependencies(self) -> List[str]:
        """Get list of available dependencies."""
        return self.available_dependencies
    
    def generate_install_command(self, package_manager: str = "pip") -> str:
        """
        Generate installation command for missing dependencies.
        
        Args:
            package_manager: Package manager to use ('pip' or 'uv')
        
        Returns:
            Installation command string
        """
        if not self.missing_dependencies:
            return "# All dependencies are available"
        
        packages = [dep['package'] for dep in self.missing_dependencies]
        
        if package_manager == "uv":
            return f"uv add {' '.join(packages)}"
        else:
            return f"pip install {' '.join(packages)}"
    
    def print_dependency_report(self):
        """Print a comprehensive dependency report."""
        print("\n" + "="*60)
        print("DEPENDENCY REPORT")
        print("="*60)
        
        if self.available_dependencies:
            print(f"\n✅ Available Dependencies ({len(self.available_dependencies)}):")
            for dep in self.available_dependencies:
                print(f"   - {dep}")
        
        if self.missing_dependencies:
            print(f"\n❌ Missing Dependencies ({len(self.missing_dependencies)}):")
            for dep in self.missing_dependencies:
                print(f"   - {dep['module']} (install: {dep['package']})")
            
            print(f"\n📦 Installation Commands:")
            print(f"   pip: {self.generate_install_command('pip')}")
            print(f"   uv:  {self.generate_install_command('uv')}")
        else:
            print("\n✅ All dependencies are available!")
        
        print("="*60)
    
    def require_dependency(self, module_name: str, package_name: Optional[str] = None) -> bool:
        """
        Require a dependency and raise an informative error if missing.
        
        Args:
            module_name: The module name to import
            package_name: The package name for installation
        
        Returns:
            True if dependency is available
        
        Raises:
            ImportError: If dependency is missing with installation instructions
        """
        if self.check_dependency(module_name, package_name):
            return True
        
        package = package_name or module_name
        raise ImportError(
            f"Missing required dependency: {module_name}\n"
            f"Install with: pip install {package}\n"
            f"Or with uv: uv add {package}"
        )


# Global dependency checker instance
dependency_checker = DependencyChecker()


def check_test_dependencies() -> Tuple[bool, List[str]]:
    """
    Check all dependencies required for testing.
    
    Returns:
        Tuple of (all_available, missing_list)
    """
    test_dependencies = {
        'pytest': 'pytest>=7.4.0',
        'pytest_asyncio': 'pytest-asyncio>=0.21.0',
        'pydantic': 'pydantic>=2.5.0',
        'pydantic_settings': 'pydantic-settings>=2.1.0',
        'sentence_transformers': 'sentence-transformers>=2.2.0',
        'lightrag': 'lightrag-hku>=1.4.0',  # Correct package name
        'psutil': 'psutil>=5.9.0',  # For system monitoring
    }
    
    results = dependency_checker.check_multiple_dependencies(test_dependencies)
    missing = [dep['package'] for dep in dependency_checker.get_missing_dependencies()]
    
    return all(results.values()), missing


def check_core_dependencies() -> Tuple[bool, List[str]]:
    """
    Check core dependencies required for basic functionality.
    
    Returns:
        Tuple of (all_available, missing_list)
    """
    core_dependencies = {
        'pydantic': 'pydantic>=2.5.0',
        'sentence_transformers': 'sentence-transformers>=2.2.0',
        'psutil': 'psutil>=5.9.0',  # For system monitoring
    }
    
    results = dependency_checker.check_multiple_dependencies(core_dependencies)
    missing = [dep['package'] for dep in dependency_checker.get_missing_dependencies()]
    
    return all(results.values()), missing


if __name__ == "__main__":
    # Run dependency check when executed directly
    print("Checking test dependencies...")
    test_available, test_missing = check_test_dependencies()
    
    print("Checking core dependencies...")
    core_available, core_missing = check_core_dependencies()
    
    dependency_checker.print_dependency_report()
    
    if not test_available:
        print(f"\n⚠️  Some test dependencies are missing. Tests may fail.")
    
    if not core_available:
        print(f"\n⚠️  Some core dependencies are missing. Core functionality may be limited.")