# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-01-28

### Added

- Compaction content trimmer callback for `before_model_callback` to prevent context bloat during long conversations
  - Location: `doc_assistant/callbacks/compaction_trimmer.py`
  - Identifies compaction contents by `"For context:"` marker in `llm_request.contents`
  - Keeps newest compaction contents within character threshold
  - Configurable via `COMPACTION_CHAR_THRESHOLD` environment variable (default: 1000)
- Events compaction config in `doc_assistant/agent.py` with `compaction_interval=10` and `overlap_size=4`
