# Archiver module

## `archiver`

Create a zip archive from configured folders and/or files.

| Argument | Required | Description |
| --- | --- | --- |
| `filename` | yes | Destination zip file path |
| `folders` | no | List of folders to include |
| `files` | no | List of files to include |

At least one of `folders` or `files` must be a non-empty list. Folder entries
are stored in the archive using their configured path as the top-level
directory name. File entries keep their configured relative path inside the
archive.

### Archive a folder

```json
{
  "module": "archiver",
  "args": {
    "filename": "results.zip",
    "folders": ["result"]
  }
}
```

### Archive individual files

```json
{
  "module": "archiver",
  "args": {
    "filename": "results.zip",
    "files": ["result/file.txt"]
  }
}
```

See the [Archiver example](../examples/archiver.md) for a runnable pipeline. The
[AppVeyor example](../examples/appveyor.md) shows archiving and uploading
artifacts in CI.
