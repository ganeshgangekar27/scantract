"""
Mock explanation responses for testing Stage 8 explanation generation.

Provides sample plain-language explanations, forbidden language examples,
and citation formatting test cases.
"""

# Valid plain-language explanation (2-4 sentences, descriptive tone)
VALID_EXPLANATION_PLAIN_LANGUAGE = (
    "This clause specifies a security deposit of 4 months' rent, which exceeds "
    "the legal limit of 2 months under the Model Tenancy Act 2021. This creates "
    "potential financial burden for tenants and may be unenforceable in disputes. "
    "Standard practice in Indian rental agreements typically caps security deposits "
    "at two months' rent to balance landlord protection with tenant affordability."
)

# Explanation with forbidden language (triggers retry)
FORBIDDEN_LANGUAGE_EXPLANATION = (
    "You should change this clause immediately. You must consult a lawyer to avoid "
    "legal issues. We recommend hiring an attorney to review this contract before signing."
)

# Valid explanation after retry (fixed forbidden language)
VALID_EXPLANATION_AFTER_RETRY = (
    "This clause differs from standard practice by requiring immediate changes. "
    "Consulting a legal professional may help clarify potential issues. "
    "Standard contracts typically include review periods before signing."
)

# Legal rule citation - raw format
LEGAL_RULE_CITATION_RAW = "Model Tenancy Act 2021, Section 7(1)"

# Legal rule citation - formatted
LEGAL_RULE_CITATION_FORMATTED = "[Legal] Model Tenancy Act 2021, §7(1)"

# Legal rule with state - raw format
LEGAL_RULE_STATE_CITATION_RAW = "Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)"

# Legal rule with state - formatted
LEGAL_RULE_STATE_CITATION_FORMATTED = "[Legal] Maharashtra Rent Control Act 1999, §11(2) (Maharashtra)"

# Corpus citation - raw format
CORPUS_CITATION_RAW = "Standard practice - fair deposit terms"

# Corpus citation - formatted
CORPUS_CITATION_FORMATTED = "[Reference] Standard practice - fair deposit terms"

# Another corpus citation example
CORPUS_CITATION_RAW_2 = "Model lease agreement - termination notice requirements"
CORPUS_CITATION_FORMATTED_2 = "[Reference] Model lease agreement - termination notice requirements"

# Explanation for missing clause
MISSING_CLAUSE_EXPLANATION = (
    "Standard residential tenancy agreements typically define division of "
    "responsibilities for maintenance and repairs. The absence of this clause "
    "creates ambiguity about whether the landlord or tenant bears responsibility "
    "for property upkeep, potentially leading to disputes."
)

# Explanation for risky clause
RISKY_CLAUSE_EXPLANATION = (
    "This clause allows termination with only 7 days notice for non-payment or breach, "
    "which differs from the Model Tenancy Act 2021 requirement of 15 days notice. "
    "This shorter timeframe may not provide tenants adequate opportunity to remedy "
    "defaults before eviction proceedings."
)

# Multi-finding mock response for batch testing
MULTI_FINDING_MOCK_RESPONSE = {
    "risky_clauses": [
        {
            "finding_id": "finding-1",
            "clause_id": 1,
            "clause_text": "Security deposit shall be 4 months' rent.",
            "clause_number": "1.1",
            "reason": "Exceeds legal limit",
            "severity": "high",
            "explanation": VALID_EXPLANATION_PLAIN_LANGUAGE,
            "formatted_citation": LEGAL_RULE_CITATION_FORMATTED
        },
        {
            "finding_id": "finding-2",
            "clause_id": 2,
            "clause_text": "Termination with 7 days notice.",
            "clause_number": "2.1",
            "reason": "Shorter than statutory requirement",
            "severity": "high",
            "explanation": RISKY_CLAUSE_EXPLANATION,
            "formatted_citation": LEGAL_RULE_CITATION_FORMATTED
        }
    ],
    "missing_clauses": [
        {
            "finding_id": "finding-3",
            "expected_clause_type": "maintenance_and_repairs",
            "reason": "Standard clause missing",
            "severity": "medium",
            "explanation": MISSING_CLAUSE_EXPLANATION,
            "formatted_citation": CORPUS_CITATION_FORMATTED
        }
    ]
}

# Citation test cases (various formats)
CITATION_TEST_CASES = [
    # Legal rules
    ("Model Tenancy Act 2021, Section 7(1)", "[Legal] Model Tenancy Act 2021, §7(1)"),
    ("Maharashtra Rent Control Act 1999, Section 11(2)", "[Legal] Maharashtra Rent Control Act 1999, §11(2)"),
    ("Transfer of Property Act 1882, Section 105", "[Legal] Transfer of Property Act 1882, §105"),
    ("Indian Contract Act 1872, Section 10", "[Legal] Indian Contract Act 1872, §10"),
    
    # Corpus references (no "Act" and "Section")
    ("Standard practice - fair deposit terms", "[Reference] Standard practice - fair deposit terms"),
    ("Model lease agreement - termination notice", "[Reference] Model lease agreement - termination notice"),
    ("Industry standard - maintenance responsibilities", "[Reference] Industry standard - maintenance responsibilities"),
]
