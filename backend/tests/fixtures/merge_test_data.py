"""
Test fixtures for merge context tests (Stage 6).

Uses REAL field names from Stage 5A and 5B models:
- LegalRuleSearchResult: id, state, act_name, section_reference, rule_text, similarity
- ReferenceClauseSearchResult: id, contract_type, clause_category, clause_text, source_label, similarity
"""

from db.legal_kb.models import LegalRuleSearchResult
from db.reference_corpus.models import ReferenceClauseSearchResult


# Unique chunks - no duplicates
def get_unique_legal_results():
    """Legal rules with unique text."""
    return [
        LegalRuleSearchResult(
            id=1,
            state="MH",
            act_name="Maharashtra Rent Control Act 1999",
            section_reference="Section 11(2)",
            rule_text="Security deposit for residential premises shall not exceed three months' rent under any circumstances.",
            similarity=0.92
        ),
        LegalRuleSearchResult(
            id=2,
            state=None,
            act_name="Model Tenancy Act 2021",
            section_reference="Section 7(1)",
            rule_text="The security deposit shall not exceed two months' rent for residential properties.",
            similarity=0.88
        ),
        LegalRuleSearchResult(
            id=3,
            state="DL",
            act_name="Delhi Rent Control Act 1958",
            section_reference="Section 6",
            rule_text="Notice period for termination must be at least three months in writing.",
            similarity=0.85
        ),
    ]


def get_unique_corpus_results():
    """Reference corpus clauses with unique text."""
    return [
        ReferenceClauseSearchResult(
            id=101,
            contract_type="rental",
            clause_category="security_deposit",
            clause_text="The security deposit shall be equivalent to two months' rent and refundable at lease end.",
            source_label="Standard practice - fair deposit terms",
            similarity=0.94
        ),
        ReferenceClauseSearchResult(
            id=102,
            contract_type="rental",
            clause_category="rent_payment",
            clause_text="Monthly rent is payable by the 5th of each month via bank transfer.",
            source_label="Common payment clause",
            similarity=0.89
        ),
        ReferenceClauseSearchResult(
            id=103,
            contract_type="freelance",
            clause_category="payment_terms",
            clause_text="Payment for services rendered shall be made within 30 days of invoice submission.",
            source_label="Standard freelance payment terms",
            similarity=0.87
        ),
    ]


# Exact duplicates - same text, different scores
def get_exact_duplicate_legal_results():
    """Two legal rules with identical text but different similarity scores."""
    return [
        LegalRuleSearchResult(
            id=10,
            state=None,
            act_name="Model Tenancy Act 2021",
            section_reference="Section 7(1)",
            rule_text="The security deposit shall not exceed two months' rent.",
            similarity=0.90
        ),
        LegalRuleSearchResult(
            id=11,
            state="MH",
            act_name="Maharashtra Rent Control Act 1999",
            section_reference="Section 11(2)",
            rule_text="The security deposit shall not exceed two months' rent.",
            similarity=0.80
        ),
    ]


# Near duplicates - 96% similar (above 0.95 threshold)
def get_near_duplicate_results():
    """Chunks with very high similarity (above threshold)."""
    return [
        LegalRuleSearchResult(
            id=20,
            state=None,
            act_name="Model Tenancy Act 2021",
            section_reference="Section 7(1)",
            rule_text="The security deposit shall not exceed two months' rent for residential properties.",
            similarity=0.91
        ),
        ReferenceClauseSearchResult(
            id=120,
            contract_type="rental",
            clause_category="security_deposit",
            clause_text="The security deposit shall not exceed two months' rent for residential properties.",
            source_label="Fair practice example",
            similarity=0.89
        ),
    ]


# Below threshold - 90% similar (below 0.95 threshold)
def get_below_threshold_results():
    """Chunks with similarity below deduplication threshold."""
    return [
        LegalRuleSearchResult(
            id=30,
            state=None,
            act_name="Model Tenancy Act 2021",
            section_reference="Section 7(1)",
            rule_text="Security deposit must not exceed two months of monthly rent.",
            similarity=0.88
        ),
        ReferenceClauseSearchResult(
            id=130,
            contract_type="rental",
            clause_category="security_deposit",
            clause_text="The tenant shall pay a security deposit of two months' rent.",
            source_label="Standard deposit clause",
            similarity=0.85
        ),
    ]


# Equal scores - test priority (legal rule should win)
def get_equal_score_results():
    """Legal rule and corpus result with identical text and same similarity."""
    return [
        LegalRuleSearchResult(
            id=40,
            state=None,
            act_name="Model Tenancy Act 2021",
            section_reference="Section 7(1)",
            rule_text="The security deposit shall be refundable within 30 days of lease termination.",
            similarity=0.90
        ),
        ReferenceClauseSearchResult(
            id=140,
            contract_type="rental",
            clause_category="security_deposit",
            clause_text="The security deposit shall be refundable within 30 days of lease termination.",
            source_label="Standard refund clause",
            similarity=0.90
        ),
    ]


# Token budget scenarios
def get_many_legal_results(count: int = 10):
    """Generate many legal rules for token budget testing."""
    results = []
    for i in range(count):
        results.append(
            LegalRuleSearchResult(
                id=50 + i,
                state="MH" if i % 2 == 0 else None,
                act_name=f"Test Act {i}",
                section_reference=f"Section {i}",
                rule_text=f"This is test legal rule number {i} with some text content to make it longer " * 10,
                similarity=0.95 - (i * 0.01)  # Descending scores
            )
        )
    return results


def get_many_corpus_results(count: int = 10):
    """Generate many corpus results for token budget testing."""
    results = []
    for i in range(count):
        results.append(
            ReferenceClauseSearchResult(
                id=150 + i,
                contract_type="rental",
                clause_category=f"category_{i}",
                clause_text=f"This is test corpus clause number {i} with some text content to make it longer " * 10,
                source_label=f"Test source {i}",
                similarity=0.94 - (i * 0.01)  # Descending scores
            )
        )
    return results


# Large chunks for minimum enforcement testing
def get_large_chunk_legal():
    """Single large legal rule (~800 tokens)."""
    return [
        LegalRuleSearchResult(
            id=60,
            state="MH",
            act_name="Maharashtra Rent Control Act 1999",
            section_reference="Section 11(2)",
            rule_text="This is a very long legal rule text. " * 100,  # ~800 tokens
            similarity=0.92
        )
    ]


def get_large_chunk_corpus():
    """Single large corpus result (~800 tokens)."""
    return [
        ReferenceClauseSearchResult(
            id=160,
            contract_type="rental",
            clause_category="security_deposit",
            clause_text="This is a very long corpus clause text. " * 100,  # ~800 tokens
            source_label="Long example clause",
            similarity=0.90
        )
    ]


# Multiple duplicates for deduplication stats testing
def get_multiple_duplicate_results():
    """10 chunks with 3 pairs of duplicates."""
    return [
        # Pair 1: duplicates (ids 70, 71)
        LegalRuleSearchResult(
            id=70, state=None, act_name="Act A", section_reference="Sec 1",
            rule_text="Duplicate text A", similarity=0.95
        ),
        LegalRuleSearchResult(
            id=71, state=None, act_name="Act B", section_reference="Sec 2",
            rule_text="Duplicate text A", similarity=0.90
        ),
        
        # Pair 2: duplicates (ids 72, 73)
        ReferenceClauseSearchResult(
            id=170, contract_type="rental", clause_category="cat1",
            clause_text="Duplicate text B", source_label="Source 1", similarity=0.88
        ),
        ReferenceClauseSearchResult(
            id=171, contract_type="rental", clause_category="cat2",
            clause_text="Duplicate text B", source_label="Source 2", similarity=0.85
        ),
        
        # Pair 3: duplicates (ids 74, 75)
        LegalRuleSearchResult(
            id=74, state=None, act_name="Act C", section_reference="Sec 3",
            rule_text="Duplicate text C", similarity=0.82
        ),
        ReferenceClauseSearchResult(
            id=172, contract_type="freelance", clause_category="cat3",
            clause_text="Duplicate text C", source_label="Source 3", similarity=0.80
        ),
        
        # 4 unique chunks
        LegalRuleSearchResult(
            id=76, state=None, act_name="Act D", section_reference="Sec 4",
            rule_text="Unique text D", similarity=0.78
        ),
        ReferenceClauseSearchResult(
            id=173, contract_type="rental", clause_category="cat4",
            clause_text="Unique text E", source_label="Source 4", similarity=0.75
        ),
        LegalRuleSearchResult(
            id=77, state=None, act_name="Act E", section_reference="Sec 5",
            rule_text="Unique text F", similarity=0.72
        ),
        ReferenceClauseSearchResult(
            id=174, contract_type="freelance", clause_category="cat5",
            clause_text="Unique text G", source_label="Source 5", similarity=0.70
        ),
    ]


# Unsorted chunks for ordering consistency testing
def get_unsorted_results():
    """Chunks with unsorted similarity scores."""
    return [
        LegalRuleSearchResult(
            id=80, state=None, act_name="Act A", section_reference="Sec 1",
            rule_text="Text A", similarity=0.70
        ),
        ReferenceClauseSearchResult(
            id=180, contract_type="rental", clause_category="cat1",
            clause_text="Text B", source_label="Source B", similarity=0.95
        ),
        LegalRuleSearchResult(
            id=81, state=None, act_name="Act B", section_reference="Sec 2",
            rule_text="Text C", similarity=0.80
        ),
        ReferenceClauseSearchResult(
            id=181, contract_type="freelance", clause_category="cat2",
            clause_text="Text D", source_label="Source D", similarity=0.90
        ),
    ]
