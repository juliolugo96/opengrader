# MVP Checklist

- [x] `opengrader run` CLI command
- [x] Strict Pydantic validation for YAML configuration
- [x] Folder-based submission discovery
- [x] Docker execution with CPU, memory, process, filesystem, and network limits
- [x] Explicit local runner for trusted development fixtures
- [x] Pass/fail scoring
- [x] JSON results
- [x] Markdown summary
- [x] Unit and CLI integration tests
- [x] Runnable example
- [x] Architecture, security, roadmap, future prompts, and premium documentation

## MVP 2

- [x] Backward-compatible partial-credit configuration
- [x] Stable submission filtering
- [x] Bounded best-attempt retries
- [x] Deterministic submission-level parallelism
- [x] Aggregate CSV report
- [x] Unit test suite
- [x] Multi-component integration test
- [x] Executable Gherkin end-to-end scenarios
- [x] Mutation testing configuration and validation
- [x] TDAID Plan, Red, Green, Refactor, and Validate record

MVP completion means the example command succeeds and the test suite passes. It
does not imply that Docker alone is sufficient for adversarial multi-tenant use;
see [SECURITY.md](SECURITY.md).
