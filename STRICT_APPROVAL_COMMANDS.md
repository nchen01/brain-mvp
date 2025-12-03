# Strict Approval Commands

This file contains a list of commands that require explicit user approval before execution to prevent accidental data loss or destructive operations.

## Commands Requiring Strict Approval

### File and Directory Deletion
- `rm` - Remove files or directories
- `rmdir` - Remove empty directories
- `unlink` - Remove files via unlink system call

### Disk and Filesystem Operations
- `dd` - Convert and copy files (can overwrite entire disks)
- `mkfs` - Create a filesystem (destroys existing data)
- `fdisk` - Partition table manipulator

### Permission and Ownership Changes
- `chmod` - Change file permissions
- `chown` - Change file owner
- `chgrp` - Change file group ownership

### Process Termination
- `kill` - Terminate processes by PID
- `pkill` - Terminate processes by name
- `killall` - Terminate all processes by name

### System Control
- `shutdown` - Shut down the system
- `reboot` - Reboot the system
- `halt` - Halt the system
- `init` - Change system runlevel

### Privilege Escalation
- `sudo` - Execute commands with superuser privileges

