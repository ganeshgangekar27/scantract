# Reference Corpus Seed Data

⚠️ **SAMPLE DATA DISCLAIMER** ⚠️

This is **sample reference data** created for demonstration and testing purposes.
These clauses are illustrative examples, NOT real legal templates or comprehensive
reference contracts.

**Do NOT use this data in production.**

## Production Requirements

In a production system, this sample data would be replaced with:

- **Vetted model contracts** reviewed and approved by legal professionals
- **Industry-standard template libraries** from recognized legal publishers
- **Jurisdiction-specific approved language** compliant with local laws
- **Regular updates** from legal counsel reflecting current regulations
- **Comprehensive coverage** of all relevant clause categories and variations

## Data Philosophy

The reference corpus serves as a **comparison baseline** in ScanTract's dual RAG pipeline:

1. **Stage 5A (Legal Rules KB)**: Retrieves applicable legal norms from Indian laws
2. **Stage 5B (Reference Corpus)**: Retrieves similar clauses from model contracts

Together, these provide context for risk detection and missing-clause identification
without giving legal advice.

### Contract Type Filtering

The system filters reference clauses by `contract_type`:
- **`rental`**: Residential rental/lease agreements
- **`freelance`**: Freelance consulting and service contracts

This ensures comparisons are made against relevant reference language.

## Embedding Model

Reference clauses are embedded using **Google Gemini's `gemini-embedding-001` model**:
- **Dimensions**: 3072
- **Search method**: Exact/brute-force cosine distance (no IVFFlat index)
- **Rationale**: Small dataset (28 clauses) doesn't benefit from approximate indexing,
  and IVFFlat cannot support >2000 dimensions

This matches the approach used in Stage 5A (Legal Rules KB) for consistency.

## Seed Data Structure

### JSON Schema

```json
{
  "contract_type": "rental" | "freelance",
  "clause_category": "string",
  "clause_text": "string",
  "source_label": "string"
}
```

### Fields

- **`contract_type`**: Contract category (`rental` or `freelance`)
- **`clause_category`**: Clause type (e.g., `rent_payment`, `payment_terms`, `termination_clause`)
- **`clause_text`**: Full clause text (verbatim from reference contract)
- **`source_label`**: Descriptive label indicating source/template name

### Clause Categories

**Rental contracts:**
- `rent_payment`: Rent amount, due dates, payment methods
- `security_deposit`: Deposit amount, refund terms
- `maintenance_charges`: Utility and maintenance responsibilities
- `termination_notice`: Notice period and termination procedures
- `lock_in_period`: Lock-in duration and early exit terms
- `repairs_maintenance`: Repair and maintenance responsibilities

**Freelance contracts:**
- `payment_terms`: Fees, invoicing, payment schedules
- `scope_of_work`: Services, deliverables, specifications
- `intellectual_property`: IP ownership and assignment
- `confidentiality`: NDA terms and confidential information handling
- `termination_clause`: Termination rights and procedures
- `indemnity`: Indemnification obligations
- `liability_limitation`: Liability caps and exclusions
- `dispute_resolution`: Arbitration, mediation, jurisdiction

## Idempotency

The seeding script uses a **unique constraint** on `(contract_type, clause_category, MD5(clause_text))`
to prevent duplicate insertions. Re-running the seed script will skip existing clauses.

## Testing

A smaller test fixture (`backend/tests/fixtures/test_reference_clauses.json`) is provided
for unit tests, containing 4-6 representative clauses.

## Future Enhancements

For production deployment:
1. **Legal review**: All clauses reviewed by qualified legal professionals
2. **Regular updates**: Quarterly reviews to reflect legal changes
3. **Expanded coverage**: 100+ clauses per contract type
4. **Regional variations**: State-specific clause language where applicable
5. **Version control**: Track clause changes over time
6. **Quality metrics**: Track clause usage and effectiveness in risk detection
