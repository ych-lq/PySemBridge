# PySemBridge Security Test Report

## Scope

This security review covers the PySemBridge tool code and supporting scripts:

- `pysembridge/`
- `tests/`
- `experiments/scripts/`
- `docs/`
- `README.md`
- `pyproject.toml`

The review intentionally excludes benchmark projects and the integrated YASA
engine copy because those directories contain external or upstream code:

- `benchmarks/`
- `integrations/`

## Goals

The goal is to confirm that the reviewed project code does not contain
intentionally planted malicious behavior, such as backdoors, credential theft,
hidden network beacons, reverse shells, destructive commands, or hard-coded
secrets.

## Checks

### Suspicious API and Shell Pattern Scan

Command:

```bash
rg -n "(eval\(|exec\(|compile\(|__import__\(|importlib\.import_module|pickle\.loads|marshal\.loads|base64\.b64decode|subprocess\.|os\.system|popen\(|socket\.|requests\.|urllib\.request|ftplib|paramiko|telnetlib|chmod|chown|setuid|setgid|rm -rf|curl |wget |nc |netcat|reverse shell|backdoor|password|token|secret|api[_-]?key)" pysembridge tests experiments/scripts docs README.md pyproject.toml
```

Result summary:

- `pysembridge/recognizer/features.py` matches `__import__`,
  `importlib.import_module`, and `pickle.loads` only as static-recognition
  pattern strings. The recognizer records those constructs when they appear in
  analyzed projects; it does not execute them.
- `pysembridge/pipeline/yasa.py` uses `subprocess.run` to invoke the configured
  YASA command with an argument list. This is expected CLI orchestration, not a
  shell backdoor.
- No `eval`, `exec`, `os.system`, socket beaconing, reverse shell, destructive
  `rm -rf`, credential exfiltration, or hard-coded secret pattern was found in
  the reviewed project code.

### Secret Pattern Scan

Command:

```bash
rg -n "BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9_]{36}|github_pat_|xox[baprs]-|sk-[A-Za-z0-9]{20,}" . -g '!benchmarks/**' -g '!integrations/**' -g '!**/__pycache__/**'
```

Result summary:

- No private keys, GitHub tokens, AWS access keys, Slack tokens, or OpenAI-style
  API keys were found in the reviewed scope.

### Executable Permission Scan

Command:

```bash
find pysembridge tests experiments/scripts -type f -not -path '*/__pycache__/*' -perm /111 -print
```

Result summary:

- No unexpected executable Python files or scripts were found in the reviewed
  scope.

### Dependency Surface Review

Command:

```bash
sed -n '1,220p' pyproject.toml
```

Result summary:

- Runtime dependencies are empty.
- `jsonschema` is optional and used only for bridge schema validation.
- The build backend uses `setuptools`.

## Functional Regression Check

Command:

```bash
python3 -m unittest discover -s tests -v
```

Expected result:

```text
test_loads_minimal_valid_bridge (test_ir_loader.BridgeLoaderValidationTest) ... ok
test_rejects_empty_gap_types (test_ir_loader.BridgeLoaderValidationTest) ... ok
test_rejects_missing_required_fields (test_ir_loader.BridgeLoaderValidationTest) ... ok
test_rejects_non_python_language (test_ir_loader.BridgeLoaderValidationTest) ... ok
test_extracts_dynamic_gap_features_from_small_sample (test_recognizer_features.RecognizerFeatureExtractionTest) ... ok

Ran 5 tests
OK
```

Coverage summary:

- Bridge loader tests confirm that valid IR can be loaded and invalid language,
  missing required fields, and empty gap types are rejected.
- Recognizer tests confirm that representative Python dynamic features are
  extracted from a compact regression fixture.
- The tests do not execute fixture-level dangerous constructs such as `eval`;
  those constructs are parsed as AST evidence for static-recognition behavior.

### CLI Availability Check

Command:

```bash
python3 -m pysembridge.cli --help
```

Expected result summary:

- The `pysembridge` CLI loads successfully.
- The help output lists `compile-yasa`, `verify-chain`, `synthesize`,
  `synthesize-auto`, `scan-gaps`, `synthesize-generic-bridge`,
  `verify-sarif`, and `run-yasa`.

## Conclusion

No evidence of intentionally planted malicious code was found in the reviewed
PySemBridge code. The only sensitive-pattern matches are explainable
static-analysis recognizer patterns or explicit YASA CLI orchestration.

Keep this report together with the exact commands above so the checks can be
reproduced later.
