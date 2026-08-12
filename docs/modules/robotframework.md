# Robot Framework modules

Both Robot Framework modules accept an ordered `arguments` list and an optional
`cwd`.

| Module | Purpose |
| --- | --- |
| `robotframework.test` | Run `python -m robot` |
| `robotframework.rebot` | Run `python -m robot.rebot` to post-process results |

## Argument format

Each string in the `arguments` list is emitted as a standalone command-line
argument. Each single-entry object is emitted as a key followed by its value;
list values emit the key followed by multiple values, and boolean `true`
emits only the key. This keeps positional arguments explicit and avoids using
`null` as a sentinel.

| Argument | Required | Description |
| --- | --- | --- |
| `arguments` | yes | Ordered Robot Framework command-line arguments |
| `cwd` | no | Working directory for the command |

## `robotframework.test`

| Argument | Required | Description |
| --- | --- | --- |
| `continueOnFailure` | no | When `true`, log robot failures and continue the stage (default: `false`) |

When `continueOnFailure` is `true`, a non-zero robot exit code is logged and
recorded, later steps in the same stage still run, and the stage fails after
all steps complete.

### Example

```json
{
  "module": "robotframework.test",
  "args": {
    "continueOnFailure": true,
    "arguments": [
      {"--outputdir": "results"},
      "tests"
    ]
  }
}
```

### Example without deferred failure

```json
{
  "module": "robotframework.test",
  "args": {
    "arguments": [
      {"--outputdir": "results"},
      "tests"
    ]
  }
}
```

## `robotframework.rebot`

### Example

```json
{
  "module": "robotframework.rebot",
  "args": {
    "arguments": [
      {"--outputdir": "results/rebot"},
      {"--name": "Builddrone Robot Example"},
      "results/output.xml"
    ]
  }
}
```

See the [Robot Framework example](../examples/robotframework.md) for a full
test and rebot pipeline.
