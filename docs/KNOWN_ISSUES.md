# Known Issues and Considerations

## 1. FieldType Enum Limits Flexibility

**Location:** `shared/models.py`

**Issue:**

The `FieldType` enum currently defines a fixed set of field types:

```python
class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    PHONE = "phone"
    EMAIL = "email"
    ID_NUMBER = "id_number"
```

This design limits the system's ability to dynamically adapt to different form types. When users need to extract fields with types not in this enum (e.g., `address`, `company_name`, `license_number`, `bank_account`), they must either:

1. Modify the source code to add new enum values
2. Use a generic type like `TEXT` and rely on the `description` field

**Impact:**
- Not suitable for multi-tenant scenarios where different users have different form schemas
- Requires code changes for each new field type
- Reduces the system's generality

**Recommended Solution:**

Replace `FieldType` enum with a plain `str` type:

```python
# Before
field_type: FieldType = Field(default=FieldType.TEXT, description="Data type")

# After
field_type: str = Field(default="text", description="Data type hint for extraction")
```

This allows users to define arbitrary field types. The VL model will use the `description` field to understand how to extract and validate values.

**Note:** The `ProcessingStatus` enum (PASS/FAIL/NEEDS_REVIEW) should remain as-is since it represents internal system states, not user-defined configurations.

**Priority:** Medium

**Status:** Open - documented for future refactoring
