"""
Custom Validators for KEGG Explore API

**What**: Reusable validation functions for complex business logic
**Why**: Centralizes validation logic that's used across multiple schemas
**How**: Import and use as Pydantic field_validator or in endpoint logic

**Usage**:
```python
from app.core.validators import validate_kegg_organism_code

# In Pydantic schema:
@field_validator('code')
def validate_code(cls, v):
    return validate_kegg_organism_code(v)

# In endpoint:
if not is_valid_organism_code(organism.code):
    raise InvalidOrganismCodeError(code=organism.code)
```
"""

import re
from typing import Optional


# =============================================================================
# KEGG Organism Code Validation
# =============================================================================

def validate_kegg_organism_code(code: str) -> str:
    """
    Validate and return KEGG organism code.

    **What**: Ensures code follows KEGG format (3-4 lowercase letters)
    **Why**: KEGG has strict organism code format
    **Returns**: Validated code (unchanged if valid)
    **Raises**: ValueError if invalid

    **Valid Examples**:
    - "eco" (Escherichia coli)
    - "hsa" (Homo sapiens)
    - "mmu" (Mus musculus)
    - "sce" (Saccharomyces cerevisiae)

    **Invalid Examples**:
    - "ECO" → uppercase not allowed
    - "e.coli" → punctuation not allowed
    - "12" → too short
    - "ECOLI" → too long + uppercase

    **KEGG Format Rules**:
    - Exactly 3 or 4 characters
    - All lowercase letters
    - No numbers, spaces, or special characters

    **Bioinformatics Note**:
    KEGG uses a 3-letter code system based on organism names:
    - First letter: genus (e: Escherichia, h: Homo, m: Mus)
    - Second/third letters: species abbreviation (co: coli, sa: sapiens)
    - Fourth letter (optional): strain/subspecies
    """
    if not isinstance(code, str):
        raise ValueError(f"Organism code must be a string, got {type(code).__name__}")

    # Strip whitespace
    code = code.strip()

    # Check length
    if len(code) < 3 or len(code) > 4:
        raise ValueError(
            f"Organism code must be 3-4 characters long. Got {len(code)} characters: '{code}'"
        )

    # Check format: 3-4 lowercase letters
    if not re.match(r'^[a-z]{3,4}$', code):
        reasons = []
        if any(c.isupper() for c in code):
            reasons.append("contains uppercase letters (must be lowercase)")
        if any(not c.isalpha() for c in code):
            reasons.append("contains non-alphabetic characters")

        reason_str = " and ".join(reasons) if reasons else "doesn't match format"
        raise ValueError(
            f"Organism code must be 3-4 lowercase letters (e.g., 'eco', 'hsa'). "
            f"Code '{code}' {reason_str}"
        )

    return code


def is_valid_organism_code(code: str) -> bool:
    """
    Check if organism code is valid without raising exception.

    **What**: Non-throwing version of validate_kegg_organism_code
    **Why**: Useful for conditional logic without try/except
    **Returns**: True if valid, False otherwise

    **Usage**:
    ```python
    if is_valid_organism_code("eco"):
        # Process valid code
    else:
        # Handle invalid code
    ```
    """
    try:
        validate_kegg_organism_code(code)
        return True
    except ValueError:
        return False


# =============================================================================
# Gene Name Validation
# =============================================================================

def validate_kegg_gene_name(name: str) -> str:
    """
    Validate KEGG gene name format.

    **What**: Ensures gene name follows KEGG format (organism:gene_id)
    **Why**: KEGG genes are namespaced by organism to avoid conflicts
    **Returns**: Validated name (unchanged if valid)
    **Raises**: ValueError if invalid

    **Valid Examples**:
    - "eco:b0001" (E. coli gene b0001)
    - "hsa:10458" (Human gene 10458)
    - "mmu:12345" (Mouse gene 12345)

    **Format**: {organism_code}:{gene_identifier}
    - organism_code: 3-4 lowercase letters
    - gene_identifier: alphanumeric + underscores

    **Note**: This is a relaxed validation - doesn't verify organism exists
    """
    if not isinstance(name, str):
        raise ValueError(f"Gene name must be a string, got {type(name).__name__}")

    name = name.strip()

    # Check for colon separator
    if ':' not in name:
        raise ValueError(
            f"Gene name must be in format 'organism:gene_id' (e.g., 'eco:b0001'). "
            f"Got: '{name}'"
        )

    # Split into organism and gene parts
    parts = name.split(':', 1)
    if len(parts) != 2:
        raise ValueError(
            f"Gene name must have exactly one colon separator. Got: '{name}'"
        )

    organism_code, gene_id = parts

    # Validate organism code part
    try:
        validate_kegg_organism_code(organism_code)
    except ValueError as e:
        raise ValueError(
            f"Invalid organism code in gene name '{name}': {e}"
        )

    # Validate gene ID part (alphanumeric + underscores, not empty)
    if not gene_id:
        raise ValueError(
            f"Gene ID cannot be empty in gene name '{name}'"
        )

    if not re.match(r'^[a-zA-Z0-9_-]+$', gene_id):
        raise ValueError(
            f"Gene ID must contain only letters, numbers, underscores, and hyphens. "
            f"Got: '{gene_id}' in '{name}'"
        )

    return name


# =============================================================================
# Status Validation
# =============================================================================

def validate_organism_status(status: Optional[str]) -> Optional[str]:
    """
    Validate organism processing status.

    **What**: Ensures status is one of the allowed values
    **Why**: Prevents typos and invalid status values
    **Returns**: Validated status (unchanged if valid)
    **Raises**: ValueError if invalid

    **Valid Values**:
    - None (null): Never processed
    - "pending": Job queued or in progress
    - "complete": Processing finished successfully
    - "error": Processing failed

    **Invalid Examples**:
    - "running" → Use "pending" instead
    - "completed" → Use "complete" instead
    - "failed" → Use "error" instead
    - "success" → Use "complete" instead
    """
    if status is None:
        return None

    valid_statuses = ("pending", "complete", "error")

    if status not in valid_statuses:
        raise ValueError(
            f"Status must be one of {valid_statuses} or null. Got: '{status}'"
        )

    return status


# =============================================================================
# Ortholog Score Validation
# =============================================================================

def validate_ortholog_identity(identity: Optional[float]) -> Optional[float]:
    """
    Validate ortholog sequence identity percentage.

    **What**: Ensures identity is in valid range (0-100%)
    **Why**: Identity percentage can't be negative or > 100%
    **Returns**: Validated identity (unchanged if valid)
    **Raises**: ValueError if out of range

    **Bioinformatics Context**:
    Sequence identity is the percentage of identical amino acids/nucleotides
    between two sequences:
    - 100%: Identical sequences
    - 70-100%: Highly similar (strong orthologs)
    - 40-70%: Moderate similarity
    - <40%: Weak similarity (may not be true orthologs)
    """
    if identity is None:
        return None

    if not isinstance(identity, (int, float)):
        raise ValueError(
            f"Identity must be a number, got {type(identity).__name__}"
        )

    if identity < 0.0 or identity > 100.0:
        raise ValueError(
            f"Identity must be between 0.0 and 100.0 percent. Got: {identity}"
        )

    return float(identity)


def validate_ortholog_score(score: Optional[int]) -> Optional[int]:
    """
    Validate Smith-Waterman alignment score.

    **What**: Ensures SW score is non-negative
    **Why**: Alignment scores can't be negative in standard SW algorithm
    **Returns**: Validated score (unchanged if valid)
    **Raises**: ValueError if negative

    **Bioinformatics Context**:
    Smith-Waterman is a dynamic programming algorithm for sequence alignment.
    Scores represent alignment quality:
    - Higher score = better alignment
    - Minimum score = 0 (no alignment)
    - Typical range: 0 to several thousand (depends on sequence length)
    """
    if score is None:
        return None

    if not isinstance(score, int):
        raise ValueError(
            f"Score must be an integer, got {type(score).__name__}"
        )

    if score < 0:
        raise ValueError(
            f"Smith-Waterman score cannot be negative. Got: {score}"
        )

    return score


# =============================================================================
# Helper Functions
# =============================================================================

def normalize_organism_code(code: str) -> str:
    """
    Normalize organism code to standard format.

    **What**: Converts code to lowercase and validates
    **Why**: Users might input "ECO" instead of "eco"
    **Returns**: Normalized code (lowercase, validated)
    **Raises**: ValueError if invalid after normalization

    **Usage**:
    ```python
    code = normalize_organism_code("ECO")  # Returns "eco"
    code = normalize_organism_code("e.coli")  # Raises ValueError
    ```
    """
    code = code.lower().strip()
    return validate_kegg_organism_code(code)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'validate_kegg_organism_code',
    'is_valid_organism_code',
    'validate_kegg_gene_name',
    'validate_organism_status',
    'validate_ortholog_identity',
    'validate_ortholog_score',
    'normalize_organism_code',
]
