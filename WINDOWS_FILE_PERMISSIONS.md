# Windows File Permissions Implementation

## Overview
This document describes the cross-platform file permission handling implemented in `core/config.py` to provide equivalent security to POSIX `chmod 0o600` on Windows systems.

## Security Goal
- **POSIX**: `chmod 0o600` - Read/write for owner only, no permissions for group/other
- **Windows Equivalent**: Remove inheritance, grant read/write to owner only, remove all other permissions

## Implementation

### Cross-Platform Function: `_secure_file_permissions()`

Located in `core/config.py`, this function:

1. **Detects platform** using `platform.system()`
2. **On POSIX (Linux/macOS)**: Uses `os.chmod(file_path, 0o600)`
3. **On Windows**: Uses `icacls.exe` command-line tool with specific security flags
4. **Graceful fallback**: Logs warnings but continues if permissions cannot be set

### Windows Implementation Details

#### Command Used:
```bash
icacls <file_path> /inheritance:r /grant:r <username>:(R,W) /remove: Everyone /remove: Users /remove: Authenticated Users
```

#### What This Does:
1. `/inheritance:r` - Removes inherited permissions from parent directories
2. `/grant:r <username>:(R,W)` - Grants read/write permissions to current user only
3. `/remove: Everyone` - Removes Everyone group permissions
4. `/remove: Users` - Removes Users group permissions  
5. `/remove: Authenticated Users` - Removes Authenticated Users permissions

#### Additional Protection:
- Sets hidden attribute: `attrib +H <file_path>`
- Multiple username retrieval methods for robustness

### Security Considerations

#### Windows vs POSIX Differences:
- **Windows uses ACLs**: Access Control Lists are more granular but complex
- **Inheritance**: Files inherit permissions from parent directories by default
- **Administrator context**: Admin accounts may have broad permissions
- **User accounts**: Standard user accounts provide better isolation

#### Equivalent Security Levels:

| Security Level | POSIX | Windows Equivalent |
|----------------|-------|-------------------|
| Owner only RW  | 0o600 | Remove inheritance + grant user RW + remove all others |
| Hidden file    | N/A   | `attrib +H` |
| Read-only      | 0o400 | `icacls /deny` or `attrib +R` |

### Error Handling & Fallbacks

The implementation includes robust error handling:

1. **File existence check**: Prevents errors on non-existent files
2. **Multiple username methods**: Tries `os.getlogin()`, environment variables, fallback
3. **icacls failure**: Logs warning but continues operation
4. **Command not found**: Logs warning and falls back gracefully
5. **Unexpected errors**: Logs warning and continues

### Testing

#### Test Files:
- `test_windows_simple.py` - Basic functionality test
- `test_cross_platform_permissions.py` - Comprehensive cross-platform test
- `test_windows_simulation.py` - Windows environment simulation

#### Test Coverage:
- ✅ POSIX permissions (0o600)
- ✅ Windows command simulation  
- ✅ Error handling scenarios
- ✅ File existence checks
- ✅ Graceful fallbacks

### Dependencies

#### Required for Windows:
- `icacls.exe` - Built-in Windows command (available on all modern Windows versions)
- Optional: `pywin32` package for more advanced Windows API access

#### Optional Enhancements:
```python
# For advanced Windows security (optional)
try:
    import win32security
    import ntsecuritycon
    # Use Windows API directly for more control
except ImportError:
    # Fall back to icacls
    pass
```

### Usage

The function is automatically called from `save_config()`:

```python
def save_config(config: LazarusConfig, config_path: Path = CONFIG_PATH) -> None:
    # ... file writing logic ...
    _secure_file_permissions(config_path)  # Secure permissions after write
```

### Platform Support

| Platform | Method | Notes |
|----------|--------|-------|
| Linux/macOS | `os.chmod(0o600)` | Native POSIX support |
| Windows 10/11 | `icacls.exe` | Requires standard Windows tools |
| Windows Server | `icacls.exe` | Works on server editions |
| WSL | `os.chmod(0o600)` | Treated as POSIX environment |

### Security Best Practices

1. **Use standard user accounts** for better permission isolation
2. **Store config in user directory** (`~/.lazarus/`) not system directories
3. **Consider encryption** for highly sensitive data beyond file permissions
4. **Regular security audits** of file permissions
5. **Monitor access attempts** through Windows Event Log

### References

- [Microsoft icacls documentation](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/icacls)
- [Python os.chmod documentation](https://docs.python.org/3/library/os.html#os.chmod)
- [Windows Access Control Lists](https://docs.microsoft.com/en-us/windows/win32/secauthz/access-control-lists)
- [POSIX file permissions](https://en.wikipedia.org/wiki/File_system_permissions#Notation_of_traditional_UNIX_permissions)