#!/usr/bin/env python3
"""Configuration management CLI tool."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.config_manager import initialize_config, Environment
from config.utils import (
    create_default_config_files, validate_config_files,
    export_config_documentation, backup_config,
    restore_config_from_backup, get_config_health_check
)
from config.schemas import get_default_config


def cmd_init(args):
    """Initialize configuration files."""
    print(f"Initializing configuration in {args.config_dir}")
    
    try:
        create_default_config_files(
            config_dir=args.config_dir,
            force=args.force
        )
        print("✓ Configuration files created successfully")
        
        if args.validate:
            result = validate_config_files(args.config_dir)
            if result["valid"]:
                print("✓ Configuration validation passed")
            else:
                print("✗ Configuration validation failed:")
                for error in result["errors"]:
                    print(f"  - {error}")
                return 1
                
    except Exception as e:
        print(f"✗ Failed to initialize configuration: {e}")
        return 1
    
    return 0


def cmd_validate(args):
    """Validate configuration files."""
    print(f"Validating configuration in {args.config_dir}")
    
    try:
        result = validate_config_files(args.config_dir)
        
        if result["valid"]:
            print("✓ All configuration files are valid")
            
            # Show file details
            for file_path, file_info in result["files"].items():
                status = "✓" if file_info["valid_yaml"] else "✗"
                print(f"  {status} {Path(file_path).name}")
        else:
            print("✗ Configuration validation failed:")
            for error in result["errors"]:
                print(f"  - {error}")
            
            if result["warnings"]:
                print("\nWarnings:")
                for warning in result["warnings"]:
                    print(f"  - {warning}")
            
            return 1
            
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        return 1
    
    return 0


def cmd_show(args):
    """Show current configuration."""
    try:
        config_manager = initialize_config(
            environment=Environment(args.environment) if args.environment else None,
            config_dir=args.config_dir,
            enable_hot_reload=False
        )
        
        if args.section:
            # Show specific section
            section_data = config_manager.get_section(args.section)
            if section_data:
                print(f"Configuration section '{args.section}':")
                print(json.dumps(section_data, indent=2, default=str))
            else:
                print(f"Section '{args.section}' not found")
                return 1
        else:
            # Show all configuration
            all_config = config_manager.get_all(mask_sensitive=not args.show_sensitive)
            print("Current configuration:")
            print(json.dumps(all_config, indent=2, default=str))
            
    except Exception as e:
        print(f"✗ Failed to show configuration: {e}")
        return 1
    
    return 0


def cmd_get(args):
    """Get specific configuration value."""
    try:
        config_manager = initialize_config(
            environment=Environment(args.environment) if args.environment else None,
            config_dir=args.config_dir,
            enable_hot_reload=False
        )
        
        value = config_manager.get(args.key, args.default)
        
        if value is not None:
            if args.json:
                print(json.dumps(value, default=str))
            else:
                print(value)
        else:
            if args.default is not None:
                print(args.default)
            else:
                print(f"Key '{args.key}' not found")
                return 1
                
    except Exception as e:
        print(f"✗ Failed to get configuration value: {e}")
        return 1
    
    return 0


def cmd_set(args):
    """Set configuration value."""
    try:
        config_manager = initialize_config(
            environment=Environment(args.environment) if args.environment else None,
            config_dir=args.config_dir,
            enable_hot_reload=False
        )
        
        # Parse value
        value = args.value
        if args.type == "int":
            value = int(value)
        elif args.type == "float":
            value = float(value)
        elif args.type == "bool":
            value = value.lower() in ("true", "1", "yes", "on")
        elif args.type == "json":
            value = json.loads(value)
        
        config_manager.set(args.key, value, persist=args.persist)
        
        print(f"✓ Set {args.key} = {value}")
        
        if args.persist:
            print("✓ Value persisted to local configuration")
            
    except Exception as e:
        print(f"✗ Failed to set configuration value: {e}")
        return 1
    
    return 0


def cmd_info(args):
    """Show configuration system information."""
    try:
        config_manager = initialize_config(
            environment=Environment(args.environment) if args.environment else None,
            config_dir=args.config_dir,
            enable_hot_reload=False
        )
        
        info = config_manager.get_config_info()
        
        print("Configuration System Information:")
        print(f"  Environment: {info['environment']}")
        print(f"  Config Directory: {info['config_dir']}")
        print(f"  Hot Reload: {info['hot_reload_enabled']}")
        print(f"  Total Config Keys: {info['total_config_keys']}")
        print(f"  Sensitive Keys: {info['sensitive_keys_count']}")
        print(f"  Validation Schemas: {info['validation_schemas_count']}")
        
        print("\nConfiguration Sources:")
        for source in info['sources']:
            status = "✓" if source['exists'] else "✗"
            print(f"  {status} {source['path']} ({source['format']}, priority: {source['priority']})")
            
    except Exception as e:
        print(f"✗ Failed to get configuration info: {e}")
        return 1
    
    return 0


def cmd_health(args):
    """Check configuration system health."""
    try:
        health_info = get_config_health_check()
        
        status_symbol = "✓" if health_info["status"] == "healthy" else "✗"
        print(f"{status_symbol} Configuration System Status: {health_info['status'].upper()}")
        
        if health_info["status"] == "healthy":
            print(f"  Environment: {health_info['environment']}")
            print(f"  Config Loaded: {health_info['config_loaded']}")
            print(f"  Hot Reload Active: {health_info['hot_reload_active']}")
            print(f"  Sources Loaded: {health_info['sources_loaded']}")
            print(f"  Config Directory Exists: {health_info['config_dir_exists']}")
            print(f"  Config Directory Writable: {health_info['config_dir_writable']}")
        else:
            print(f"  Error: {health_info.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return 1
    
    return 0


def cmd_backup(args):
    """Create configuration backup."""
    try:
        config_manager = initialize_config(
            environment=Environment(args.environment) if args.environment else None,
            config_dir=args.config_dir,
            enable_hot_reload=False
        )
        
        backup_file = backup_config(config_manager, args.backup_dir)
        
        if backup_file:
            print(f"✓ Configuration backup created: {backup_file}")
        else:
            print("✗ Failed to create backup")
            return 1
            
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return 1
    
    return 0


def cmd_restore(args):
    """Restore configuration from backup."""
    try:
        config_manager = initialize_config(
            environment=Environment(args.environment) if args.environment else None,
            config_dir=args.config_dir,
            enable_hot_reload=False
        )
        
        restore_config_from_backup(args.backup_file, config_manager)
        
        print(f"✓ Configuration restored from: {args.backup_file}")
        
    except Exception as e:
        print(f"✗ Restore failed: {e}")
        return 1
    
    return 0


def cmd_docs(args):
    """Generate configuration documentation."""
    try:
        config_manager = initialize_config(
            environment=Environment(args.environment) if args.environment else None,
            config_dir=args.config_dir,
            enable_hot_reload=False
        )
        
        export_config_documentation(config_manager, args.output)
        
        print(f"✓ Configuration documentation generated: {args.output}")
        
    except Exception as e:
        print(f"✗ Documentation generation failed: {e}")
        return 1
    
    return 0


def cmd_template(args):
    """Generate configuration template."""
    try:
        if args.format == "yaml":
            import yaml
            default_config = get_default_config()
            
            with open(args.output, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
        else:
            default_config = get_default_config()
            
            with open(args.output, 'w') as f:
                json.dump(default_config, f, indent=2, default=str)
        
        print(f"✓ Configuration template generated: {args.output}")
        
    except Exception as e:
        print(f"✗ Template generation failed: {e}")
        return 1
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DocForge Configuration Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init                          # Initialize default config files
  %(prog)s validate                      # Validate configuration
  %(prog)s show                          # Show all configuration
  %(prog)s show --section database       # Show database configuration
  %(prog)s get database.host             # Get specific value
  %(prog)s set database.port 5433        # Set configuration value
  %(prog)s info                          # Show system information
  %(prog)s health                        # Check system health
  %(prog)s backup                        # Create configuration backup
  %(prog)s docs --output config.md       # Generate documentation
        """
    )
    
    # Global options
    parser.add_argument(
        "--config-dir", "-c",
        default="config",
        help="Configuration directory (default: config)"
    )
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "testing", "staging", "production"],
        help="Environment to use"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize configuration files")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    init_parser.add_argument("--validate", action="store_true", help="Validate after creation")
    init_parser.set_defaults(func=cmd_init)
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration files")
    validate_parser.set_defaults(func=cmd_validate)
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show configuration")
    show_parser.add_argument("--section", help="Show specific section")
    show_parser.add_argument("--show-sensitive", action="store_true", help="Show sensitive values")
    show_parser.set_defaults(func=cmd_show)
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get configuration value")
    get_parser.add_argument("key", help="Configuration key (dot notation)")
    get_parser.add_argument("--default", help="Default value if key not found")
    get_parser.add_argument("--json", action="store_true", help="Output as JSON")
    get_parser.set_defaults(func=cmd_get)
    
    # Set command
    set_parser = subparsers.add_parser("set", help="Set configuration value")
    set_parser.add_argument("key", help="Configuration key (dot notation)")
    set_parser.add_argument("value", help="Value to set")
    set_parser.add_argument("--type", choices=["str", "int", "float", "bool", "json"], default="str", help="Value type")
    set_parser.add_argument("--persist", action="store_true", help="Persist to local config file")
    set_parser.set_defaults(func=cmd_set)
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show configuration system information")
    info_parser.set_defaults(func=cmd_info)
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Check configuration system health")
    health_parser.set_defaults(func=cmd_health)
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create configuration backup")
    backup_parser.add_argument("--backup-dir", default="config_backups", help="Backup directory")
    backup_parser.set_defaults(func=cmd_backup)
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore configuration from backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore from")
    restore_parser.set_defaults(func=cmd_restore)
    
    # Docs command
    docs_parser = subparsers.add_parser("docs", help="Generate configuration documentation")
    docs_parser.add_argument("--output", default="config_documentation.md", help="Output file")
    docs_parser.set_defaults(func=cmd_docs)
    
    # Template command
    template_parser = subparsers.add_parser("template", help="Generate configuration template")
    template_parser.add_argument("--output", default="config_template.yaml", help="Output file")
    template_parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="Output format")
    template_parser.set_defaults(func=cmd_template)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n✗ Operation cancelled")
        return 1
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())