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

## Exit codes

`robot` and `rebot` use the same return codes. Builddrone treats test-result
codes differently from tool errors:

| Exit code | Meaning | Stage behavior |
| --- | --- | --- |
| 0 | All tests passed | Continue |
| 1-249 | That many tests failed | Log the failure, continue later steps, fail the stage at the end |
| 250 | 250 or more tests failed | Log the failure, continue later steps, fail the stage at the end |
| 251 | Help or version printed | Stop immediately |
| 252 | Invalid data or command line options, including a missing file | Stop immediately |
| 253 | Execution stopped by the user | Stop immediately |
| 255 | Unexpected internal error | Stop immediately |

That lets a `test` stage keep going after failed tests so later steps such as
`robotframework.rebot` can still generate combined reports. The stage still
fails after all steps complete.

## `robotframework.test`

### Example

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
