#!/usr/bin/env python3
"""
DocForge Brain MVP - Version Backup Script

This script creates a complete backup of the current system state,
allowing you to revert to v1.0 if future integrations cause issues.
"""

import os
import shutil
import subprocess
import tarfile
import json
from datetime import datetime
from pathlib import Path


def create_backup(backup_name: str = None):
    """Create a complete backup of the current system state."""
    
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"docforge_mvp_backup_{timestamp}"
    
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    backup_path = backup_dir / f"{backup_name}.tar.gz"
    
    print(f"🔄 Creating backup: {backup_path}")
    
    # Files and directories to include in backup
    include_patterns = [
        "src/",
        "tests/", 
        "scripts/",
        "docs/",
        "examples/",
        "config/",
        ".kiro/",
        "*.md",
        "*.py",
        "*.yaml",
        "*.yml", 
        "*.toml",
        "*.txt",
        ".gitignore",
        ".env.example"
    ]
    
    # Files and directories to exclude
    exclude_patterns = [
        "__pycache__/",
        "*.pyc",
        ".pytest_cache/",
        ".venv/",
        "venv/",
        ".git/",
        "data/",
        "temp/",
        "output/",
        "logs/",
        "*.log",
        "*.db",
        "*.sqlite*",
        ".DS_Store",
        "Thumbs.db",
        "backups/"
    ]
    
    # Create tar.gz backup
    with tarfile.open(backup_path, "w:gz") as tar:
        for pattern in include_patterns:
            for item in Path(".").glob(pattern):
                if item.is_file() or item.is_dir():
                    # Check if item should be excluded
                    should_exclude = False
                    for exclude_pattern in exclude_patterns:
                        if item.match(exclude_pattern) or any(part.startswith('.') and part != '.env.example' and part != '.gitignore' for part in item.parts):
                            should_exclude = True
                            break
                    
                    if not should_exclude:
                        print(f"  Adding: {item}")
                        tar.add(item, arcname=item)
    
    # Create backup metadata
    metadata = {
        "backup_name": backup_name,
        "created_at": datetime.now().isoformat(),
        "git_commit": get_git_commit(),
        "git_tag": get_git_tag(),
        "system_info": get_system_info(),
        "validation_status": get_validation_status()
    }
    
    metadata_path = backup_dir / f"{backup_name}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Backup created successfully!")
    print(f"📁 Backup file: {backup_path}")
    print(f"📋 Metadata: {metadata_path}")
    print(f"📊 Backup size: {backup_path.stat().st_size / (1024*1024):.1f} MB")
    
    return backup_path, metadata_path


def get_git_commit():
    """Get current git commit hash."""
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        return "unknown"


def get_git_tag():
    """Get current git tag."""
    try:
        result = subprocess.run(['git', 'describe', '--tags', '--exact-match'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        return "no-tag"


def get_system_info():
    """Get system information."""
    import platform
    import sys
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture(),
        "processor": platform.processor()
    }


def get_validation_status():
    """Get current validation status."""
    try:
        # Run validation and capture results
        result = subprocess.run(['python', 'scripts/run_final_validation.py'], 
                              capture_output=True, text=True, timeout=60)
        
        # Parse validation results
        if "100.0%" in result.stdout and "READY" in result.stdout:
            return {
                "status": "PRODUCTION_READY",
                "success_rate": "100%",
                "tests_passed": "11/11"
            }
        else:
            return {
                "status": "NEEDS_ATTENTION", 
                "output": result.stdout[-500:]  # Last 500 chars
            }
    except:
        return {"status": "VALIDATION_FAILED"}


def restore_backup(backup_path: str):
    """Restore from a backup (use with caution!)."""
    backup_file = Path(backup_path)
    
    if not backup_file.exists():
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    print(f"⚠️  WARNING: This will overwrite current files!")
    print(f"📁 Restoring from: {backup_path}")
    
    confirm = input("Type 'RESTORE' to confirm: ")
    if confirm != "RESTORE":
        print("❌ Restore cancelled")
        return False
    
    # Extract backup
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall(".")
    
    print("✅ Backup restored successfully!")
    print("🔄 You may need to:")
    print("   - Reinstall dependencies: uv sync")
    print("   - Check configuration files")
    print("   - Run validation: python scripts/run_final_validation.py")
    
    return True


def list_backups():
    """List all available backups."""
    backup_dir = Path("backups")
    
    if not backup_dir.exists():
        print("📁 No backups directory found")
        return
    
    backups = list(backup_dir.glob("*.tar.gz"))
    
    if not backups:
        print("📁 No backups found")
        return
    
    print("📋 Available backups:")
    for backup in sorted(backups):
        metadata_file = backup_dir / f"{backup.stem}_metadata.json"
        
        size_mb = backup.stat().st_size / (1024*1024)
        print(f"  📦 {backup.name} ({size_mb:.1f} MB)")
        
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)
                print(f"     📅 Created: {metadata.get('created_at', 'unknown')}")
                print(f"     🏷️  Tag: {metadata.get('git_tag', 'unknown')}")
                print(f"     ✅ Status: {metadata.get('validation_status', {}).get('status', 'unknown')}")
            except:
                pass
        print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            backup_name = sys.argv[2] if len(sys.argv) > 2 else None
            create_backup(backup_name)
            
        elif command == "restore":
            if len(sys.argv) < 3:
                print("Usage: python scripts/create_v1_backup.py restore <backup_file>")
                sys.exit(1)
            restore_backup(sys.argv[2])
            
        elif command == "list":
            list_backups()
            
        else:
            print("Unknown command. Use: create, restore, or list")
            
    else:
        print("DocForge Brain MVP - Backup Management")
        print("Usage:")
        print("  python scripts/create_v1_backup.py create [backup_name]")
        print("  python scripts/create_v1_backup.py restore <backup_file>")
        print("  python scripts/create_v1_backup.py list")
        print()
        print("Examples:")
        print("  python scripts/create_v1_backup.py create v1_stable")
        print("  python scripts/create_v1_backup.py restore backups/v1_stable.tar.gz")
        print("  python scripts/create_v1_backup.py list")