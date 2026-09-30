# Preflight environment

Default Homebrew Python 3.14 lacked NumPy (collection errors). An isolated Python 3.12 virtualenv with `.[test]` plus NumPy exposed missing sentencepiece/JAX imports. Installing the repository-declared `.[test,train]` extras resolved those failures: 545 passed, 7 skipped, 11 deselected. No test or product source was modified. These were environment setup failures, not candidate-model calls.

Root cause: the default interpreter did not contain the repository test/train dependencies; fix site: an isolated virtualenv, leaving system Python and project dependencies unchanged.
