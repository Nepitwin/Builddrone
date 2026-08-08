# Twine modules

## `twine.upload`

Upload distribution files to a package index with
[twine](https://twine.readthedocs.io/). Each entry in `files` is a glob pattern;
matched files are uploaded in one twine command per pattern.

Tag-based deployment should be handled outside this module, for example by
running the upload stage only on tagged CI builds.

| Argument | Required | Description |
| --- | --- | --- |
| `files` | yes | Non-empty list of glob patterns selecting files to upload |
| `skip_existing` | no | Skip files that already exist on the index (default: `true`) |
| `repository` | no | Upload URL passed to `twine --repository-url` |

### Example

```json
{
  "module": "twine.upload",
  "args": {
    "files": ["dist/*.whl", "dist/*.tar.gz"],
    "skip_existing": true
  }
}
```

Set `"skip_existing": false` to omit `--skip-existing` and fail when a file
already exists on the index.

### Custom upload URL

```json
{
  "module": "twine.upload",
  "args": {
    "files": ["dist/*.whl", "dist/*.tar.gz"],
    "repository": "https://upload.pypi.org/legacy/"
  }
}
```

Omit `repository` to use twine's default upload target.

### Tag deployment in CI

Keep upload generic and gate the stage in CI. On AppVeyor:

```yaml
deploy:
  - ps: |
      if ($env:APPVEYOR_REPO_TAG -eq 'true') {
        python -m builddrone deploy
      } else {
        Write-Output "No tag for deployment"
      }
```

The `deploy` stage in `blueprint.json` can then call `twine.upload` without
checking tags itself.
