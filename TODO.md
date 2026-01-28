# TODO

## High Priority

### [ ] Tokenizer-based Compaction Trimming

**Location:** `doc_assistant/callbacks/compaction_trimmer.py`

**Problem:**
The current compaction trimmer uses character count as a rough approximation for context size. This is inaccurate because LLM context limits are measured in tokens, not characters.

**Proposed Solution:**
- [ ] Replace character-based threshold with tokenizer-based calculation
- [ ] Use `tiktoken` or model-specific tokenizer for accurate token counting
- [ ] Update environment variable from `COMPACTION_CHAR_THRESHOLD` to `COMPACTION_TOKEN_THRESHOLD`

**Acceptance Criteria:**
- Trimming decisions based on actual token count
- Configurable token threshold via environment variable
- Backward compatible with existing configuration
