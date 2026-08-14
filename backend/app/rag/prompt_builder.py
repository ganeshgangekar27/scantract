"""
LangChain Prompt Template Loading and Assembly for ScanTract

This module provides functions to build LangChain-compatible prompts for contract analysis.
Templates are loaded from backend/rag/prompts/*.txt files and cached in memory for performance.

Usage:
    # Classification prompt
    messages = build_classification_prompt(
        clause_text="Tenant shall pay rent by the 5th of each month.",
        clause_index="1.1",
        contract_type="rental",
        retrieved_context="Model Tenancy Act Section 5..."
    )
    
    # Risk detection prompt
    messages = build_risk_prompt(
        clauses_list=[
            {"clause_id": "1", "clause_type": "payment", "clause_text": "..."},
            {"clause_id": "2", "clause_type": "termination", "clause_text": "..."}
        ],
        retrieved_context="Legal rules and corpus examples...",
        contract_type="rental"
    )

Note: Templates are loaded lazily and cached. The first call to each builder function
will read from disk; subsequent calls use the in-memory cache.

Template files location: backend/rag/prompts/
- clause_classification.txt
- risk_detection.txt
"""

from pathlib import Path
from typing import Any
import logging
import re

# Module-level constants
PROMPTS_DIR = Path(__file__).parent.parent.parent / "rag" / "prompts"
_template_cache: dict[str, str] = {}

# Logger setup
logger = logging.getLogger(__name__)


def _load_template(template_name: str) -> str:
    """
    Load a prompt template from disk with caching.
    
    Templates are loaded once and cached in memory. Subsequent calls
    return the cached version without file I/O.
    
    Args:
        template_name: Name of template file without .txt extension
                      (e.g., "clause_classification")
    
    Returns:
        Template content as string with {variable} placeholders
    
    Raises:
        FileNotFoundError: If template file doesn't exist at expected path
    """
    # Check cache first
    if template_name in _template_cache:
        logger.debug(f"Template '{template_name}' loaded from cache")
        return _template_cache[template_name]
    
    # Construct file path
    template_path = PROMPTS_DIR / f"{template_name}.txt"
    
    # Verify file exists
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template file not found: {template_path}\n"
            f"Expected location: {template_path.absolute()}"
        )
    
    # Read template content
    logger.info(f"Loading template '{template_name}' from {template_path}")
    template_content = template_path.read_text(encoding="utf-8")
    
    # Cache for future use
    _template_cache[template_name] = template_content
    logger.info(f"Template '{template_name}' loaded and cached successfully")
    
    return template_content


def _validate_no_placeholders(prompt: str, template_name: str) -> None:
    """
    Validate that no unfilled {variable} placeholders remain in prompt.
    
    After variable substitution, this function ensures all placeholders
    were properly filled. Raises an error if any remain unfilled.
    
    This function distinguishes between:
    - Template placeholders: {variable_name} - should be replaced
    - JSON syntax: {"key": "value"} - should be preserved
    
    Args:
        prompt: The assembled prompt string to validate
        template_name: Name of template (for error messages)
    
    Raises:
        ValueError: If any {variable} placeholders remain unfilled
    """
    # Find template-style placeholders: {word_with_underscores}
    # This pattern matches {var_name} but NOT {"json": "syntax"}
    # Pattern explanation: { followed by word characters/underscores only, then }
    placeholder_pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
    matches = re.findall(placeholder_pattern, prompt)
    
    if matches:
        placeholder_list = ", ".join(matches)
        raise ValueError(
            f"Unfilled placeholders in {template_name} template: {placeholder_list}\n"
            f"This indicates missing required variables."
        )
    
    logger.debug(f"Validation passed for {template_name}: no unfilled placeholders")


def build_classification_prompt(
    clause_text: str,
    clause_index: str,
    contract_type: str,
    retrieved_context: str
) -> list[dict[str, str]]:
    """
    Build a clause classification prompt from template.
    
    Loads the clause_classification.txt template, fills all required variables,
    and returns a LangChain-compatible message array.
    
    Args:
        clause_text: The clause content to classify
        clause_index: Clause identifier (e.g., "1.1", "para_5")
        contract_type: "rental" or "freelance"
        retrieved_context: RAG-retrieved context from Stage 5A/5B
    
    Returns:
        LangChain-compatible message array: [{"role": "user", "content": "..."}]
    
    Raises:
        FileNotFoundError: If template file doesn't exist
        ValueError: If any variables remain unfilled (indicates a bug)
    """
    # Load template
    template = _load_template("clause_classification")
    
    # Perform variable substitution
    filled_template = template.replace("{clause_text}", clause_text)
    filled_template = filled_template.replace("{clause_index}", clause_index)
    filled_template = filled_template.replace("{contract_type}", contract_type)
    filled_template = filled_template.replace("{retrieved_context}", retrieved_context)
    
    # Validate no placeholders remain
    _validate_no_placeholders(filled_template, "clause_classification")
    
    # Return LangChain message format
    return [{"role": "user", "content": filled_template}]


def build_risk_prompt(
    clauses_list: list[dict[str, Any]],
    retrieved_context: str,
    contract_type: str
) -> list[dict[str, str]]:
    """
    Build a risk detection prompt from template.
    
    Loads the risk_detection.txt template, formats the clauses list,
    fills all required variables, and returns a LangChain-compatible message array.
    
    Note: This function uses a single 'retrieved_context' parameter (not separate
    legal_context/corpus_context) per the design reconciliation documented in
    design.md. Stage 6 merges contexts before Stage 7 calls this function.
    
    Args:
        clauses_list: List of clause dicts with keys: clause_id, clause_type, clause_text
        retrieved_context: Single merged context from Stage 6 (includes both legal rules
                          and reference corpus examples already merged and deduplicated)
        contract_type: "rental" or "freelance"
    
    Returns:
        LangChain-compatible message array: [{"role": "user", "content": "..."}]
    
    Raises:
        FileNotFoundError: If template file doesn't exist
        ValueError: If any variables remain unfilled (indicates a bug)
    """
    # Format clauses_list into human-readable text
    formatted_clauses = []
    for clause in clauses_list:
        clause_id = clause.get("clause_id", "unknown")
        clause_type = clause.get("clause_type", "unknown")
        clause_text = clause.get("clause_text", "")
        formatted_clauses.append(
            f"Clause {clause_id} ({clause_type}): {clause_text}"
        )
    
    clauses_text = "\n\n".join(formatted_clauses)
    
    # Load template
    template = _load_template("risk_detection")
    
    # Perform variable substitution
    filled_template = template.replace("{clauses_list}", clauses_text)
    filled_template = filled_template.replace("{retrieved_context}", retrieved_context)
    filled_template = filled_template.replace("{contract_type}", contract_type)
    
    # Validate no placeholders remain
    _validate_no_placeholders(filled_template, "risk_detection")
    
    # Return LangChain message format
    return [{"role": "user", "content": filled_template}]
