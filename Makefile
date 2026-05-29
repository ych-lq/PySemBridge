.PHONY: test pycompile code-stats security-check scan-fixture

test:
	python3 -m unittest discover -s tests

pycompile:
	python3 -m py_compile pysembridge/recognizer/features.py pysembridge/recognizer/classifier.py tests/fixtures/recognizer_gaps/dynamic_gap_sample.py tests/test_recognizer_features.py tests/test_ir_loader.py

code-stats:
	find pysembridge -type f -name '*.py' -not -path '*/__pycache__/*' -print0 | xargs -0 wc -l
	find pysembridge tests experiments/scripts -type f -not -path '*/__pycache__/*' -print0 | xargs -0 wc -l

security-check:
	rg -n "(eval\\(|exec\\(|compile\\(|__import__\\(|importlib\\.import_module|pickle\\.loads|marshal\\.loads|base64\\.b64decode|subprocess\\.|os\\.system|popen\\(|socket\\.|requests\\.|urllib\\.request|ftplib|paramiko|telnetlib|chmod|chown|setuid|setgid|rm -rf|curl |wget |nc |netcat|reverse shell|backdoor|password|token|secret|api[_-]?key)" pysembridge tests experiments/scripts docs README.md pyproject.toml || true
	rg -n "BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9_]{36}|github_pat_|xox[baprs]-|sk-[A-Za-z0-9]{20,}" . -g '!benchmarks/**' -g '!integrations/**' -g '!**/__pycache__/**' || true
	find pysembridge tests experiments/scripts -type f -not -path '*/__pycache__/*' -perm /111 -print

scan-fixture:
	python3 -m pysembridge.cli scan-gaps --project tests/fixtures/recognizer_gaps --project-name recognizer-fixture --output /tmp/pysembridge-recognizer-fixture.json --include-features
