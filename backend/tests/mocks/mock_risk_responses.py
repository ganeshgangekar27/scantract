"""
Mock LLM responses for risk detection testing.

Provides predefined responses for testing various scenarios:
- Valid responses with proper traceability
- Invalid responses missing traceability fields
- Malformed JSON responses
- Markdown-wrapped responses
"""

# Valid response with all required fields properly populated
VALID_RISK_RESPONSE = {
    "risky_clauses": [
        {
            "clause_id": "1.1",
            "reason": "Deposit amount exceeds legal limit of 2 months rent, creating financial burden on tenant",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 7(1) - Maximum deposit is 2 months rent",
            "severity": "high"
        },
        {
            "clause_id": "2.3",
            "reason": "Termination notice period of 7 days is significantly shorter than standard 30-day period",
            "triggering_rule_or_corpus": "Standard practice - fair termination notice period (Reference: Sample Rental Agreement, Clause 8)",
            "severity": "medium"
        }
    ],
    "missing_clauses": [
        {
            "expected_clause_type": "maintenance_responsibilities",
            "why_expected": "Contract does not specify who is responsible for repairs and maintenance of the property",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 5(2) - Maintenance responsibilities must be clearly defined",
            "severity": "low"
        }
    ]
}


# Response with missing triggering_rule_or_corpus field
# This should trigger traceability validation failure
MISSING_TRACEABILITY_RESPONSE = {
    "risky_clauses": [
        {
            "clause_id": "1.1",
            "reason": "Deposit amount exceeds legal limit of 2 months rent",
            "triggering_rule_or_corpus": "",  # EMPTY - should be rejected
            "severity": "high"
        }
    ],
    "missing_clauses": []
}


# Another variant with field missing entirely
MISSING_TRACEABILITY_FIELD_RESPONSE = {
    "risky_clauses": [],
    "missing_clauses": [
        {
            "expected_clause_type": "dispute_resolution",
            "why_expected": "No dispute resolution mechanism specified in the contract",
            # "triggering_rule_or_corpus" field is completely missing
            "severity": "medium"
        }
    ]
}


# Malformed JSON - missing closing brace
MALFORMED_JSON_RESPONSE = """{
    "risky_clauses": [
        {
            "clause_id": "1.1",
            "reason": "Excessive deposit amount specified",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 7(1)",
            "severity": "high"
        }
    ],
    "missing_clauses": []
"""
# Note: Missing closing brace - this should fail JSON parsing


# Valid JSON wrapped in markdown code fence
# Should be successfully parsed after stripping
MARKDOWN_WRAPPED_RESPONSE = """```json
{
    "risky_clauses": [
        {
            "clause_id": "3.1",
            "reason": "Rent increase clause allows arbitrary increases without any cap or justification",
            "triggering_rule_or_corpus": "Standard practice - rent increases should be capped at inflation rate",
            "severity": "high"
        }
    ],
    "missing_clauses": [
        {
            "expected_clause_type": "security_deposit_return",
            "why_expected": "No clause specifying timeline and conditions for security deposit return",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 22 - Deposit return timeline must be specified",
            "severity": "medium"
        }
    ]
}
```"""


# Empty response - no risks or missing clauses found
EMPTY_RISK_RESPONSE = {
    "risky_clauses": [],
    "missing_clauses": []
}


# Response with multiple severity levels for testing severity counting
MULTI_SEVERITY_RESPONSE = {
    "risky_clauses": [
        {
            "clause_id": "1.1",
            "reason": "Critical issue with payment terms creating severe financial burden",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 7(1)",
            "severity": "high"
        },
        {
            "clause_id": "1.2",
            "reason": "Another critical issue with liability terms",
            "triggering_rule_or_corpus": "Standard practice - reasonable liability limits",
            "severity": "high"
        },
        {
            "clause_id": "2.1",
            "reason": "Moderately problematic termination clause",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 12",
            "severity": "medium"
        },
        {
            "clause_id": "2.2",
            "reason": "Another moderate issue with notice period",
            "triggering_rule_or_corpus": "Standard practice - fair notice period",
            "severity": "medium"
        },
        {
            "clause_id": "2.3",
            "reason": "Yet another moderate issue",
            "triggering_rule_or_corpus": "Reference: Sample Contract, Clause 5",
            "severity": "medium"
        }
    ],
    "missing_clauses": [
        {
            "expected_clause_type": "force_majeure",
            "why_expected": "Minor omission - force majeure clause provides useful protection",
            "triggering_rule_or_corpus": "Standard practice - force majeure clauses are recommended",
            "severity": "low"
        }
    ]
}


# Response with invalid clause_id reference (for testing warning/skip behavior)
INVALID_CLAUSE_ID_RESPONSE = {
    "risky_clauses": [
        {
            "clause_id": "99.99",  # This clause ID doesn't exist
            "reason": "This references a non-existent clause and should be skipped with a warning",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 7(1)",
            "severity": "high"
        },
        {
            "clause_id": "1.1",  # This one is valid
            "reason": "Valid clause reference that should be persisted",
            "triggering_rule_or_corpus": "Standard practice - fair terms",
            "severity": "medium"
        }
    ],
    "missing_clauses": []
}


# Response with various citation formats (testing flexibility)
CITATION_FORMAT_VARIETY_RESPONSE = {
    "risky_clauses": [
        {
            "clause_id": "1.1",
            "reason": "Issue with rent amount",
            "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 7(1)",
            "severity": "high"
        },
        {
            "clause_id": "1.2",
            "reason": "Issue with deposit terms",
            "triggering_rule_or_corpus": "Standard practice - fair deposit terms",
            "severity": "medium"
        }
    ],
    "missing_clauses": [
        {
            "expected_clause_type": "maintenance",
            "why_expected": "Maintenance responsibilities not specified",
            "triggering_rule_or_corpus": "Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)",
            "severity": "low"
        }
    ]
}
