# Filesystem modules

## `filesystem.copy`

Copy a directory tree, optionally filtering files with a glob.

| Argument | Required | Description |
| --- | --- | --- |
| `source` | yes | Source directory |
| `destination` | yes | Destination directory |
| `files` | no | Glob filter such as `*.jpg` |

### Example

```json
{
  "module": "filesystem.copy",
  "args": {
    "source": "example",
    "files": "*.jpg",
    "destination": "example_copy_files"
  }
}
```

## `filesystem.cleanup`

Remove listed files and folders.

| Argument | Required | Description |
| --- | --- | --- |
| `files` | no | List of file paths to delete |
| `folders` | no | List of folder paths to delete |

### Example

```json
{
  "module": "filesystem.cleanup",
  "args": {
    "folders": [".venv", "dist"],
    "files": ["my_file.json"]
  }
}
```

See the [Python example](../examples/python.md) for a cleanup stage that removes
build artifacts.
