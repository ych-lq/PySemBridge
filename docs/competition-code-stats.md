# Competition Code Statistics

This document records the code ownership and line-count scope for competition
submission.

## Counted Scope

The independent PySemBridge implementation is counted from:

- `pysembridge/`: core Python package, CLI, recognizer, synthesizer, adapters,
  pipeline, verifier, and Semantic Bridge schema.
- `tests/`: self-developed regression tests and compact fixtures.
- `experiments/scripts/`: reproducible shell wrappers for PySemBridge/YASA runs.
- `docs/`: self-developed documentation.

The strictest source-code-only scope is `pysembridge/`.

## Excluded Scope

The following directories are excluded from independent-code statistics:

- `benchmarks/`: third-party CVE benchmark projects.
- `integrations/yasa/`: integrated upstream YASA engine copy.
- `experiments/results/`: generated reports and run outputs.
- `__pycache__/`, build outputs, dependency directories, and local environment
  files.

## Reproducible Commands

Core package Python source:

```bash
find pysembridge -type f -name '*.py' -not -path '*/__pycache__/*' -print0 | xargs -0 wc -l
```

Current result:

```text
2652 total lines in pysembridge/*.py
```

Core package plus tests and reproducible scripts:

```bash
find pysembridge tests experiments/scripts -type f -not -path '*/__pycache__/*' -print0 | xargs -0 wc -l
```

Current result:

```text
3333 total lines
```

## Conclusion

Even under the strict `pysembridge/`-only source-code scope, the repository
exceeds the 1000-line independent-development requirement. Third-party
benchmarks and the integrated YASA engine are deliberately excluded from this
count.
