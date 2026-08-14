# Legal Rules Knowledge Base - Seed Data

## ⚠️ SAMPLE DATA DISCLAIMER

**The legal rules in this directory are SAMPLE DATA ONLY and are NOT suitable for production use.**

This seed dataset contains simplified, illustrative legal provisions for development and testing purposes. These samples:

- Are not comprehensive legal references
- May be outdated or incomplete
- Are not validated by legal professionals
- Should NEVER be used for actual contract analysis in production

## Production Replacement Checklist

Before deploying to production, you MUST:

- [ ] Replace with professionally curated legal database
- [ ] Validate all provisions with qualified legal counsel
- [ ] Implement jurisdiction-specific rule sets for all supported states
- [ ] Add regular update mechanisms for legal changes
- [ ] Include metadata (effective dates, amendment tracking, case law references)
- [ ] Obtain proper licensing for commercial legal databases if used

## Data Sources for Production

Consider these authoritative sources for production legal data:

- **India Code** (https://www.indiacode.nic.in/) - Official central and state legislation
- **Legislative Department, Ministry of Law and Justice** - Acts and amendments
- **State Government Gazettes** - State-specific regulations
- **Commercial Legal Databases** - LexisNexis, Manupatra, SCC Online (requires licensing)

## Current Sample Data

- **Source**: Manually created illustrative examples
- **Coverage**: Model Tenancy Act 2021, Indian Contract Act 1872, 4 state-specific samples
- **Last Updated**: August 2026 (generated at seed time)
- **Entry Count**: 20 sample rules
- **States Covered**: Maharashtra (MH), Karnataka (KA), Delhi (DL), Tamil Nadu (TN)
- **Central Laws**: Model Tenancy Act 2021 (12 provisions), Indian Contract Act 1872 (3 provisions)
- **State Laws**: 4 state-specific provisions

## File Format

The `legal_rules.json` file contains an array of legal rule objects with the following structure:

```json
{
  "state": null,
  "act_name": "Model Tenancy Act 2021",
  "section_reference": "Section 7(1)",
  "rule_text": "Full text of the legal provision..."
}
```

- `state`: Two-letter state code (e.g., "MH", "KA") or `null` for central laws
- `act_name`: Full name of the act or statute
- `section_reference`: Section/clause identifier
- `rule_text`: Complete text of the legal provision with context

## Usage

To load this sample data into the database:

```bash
python -m backend.db.legal_kb.seed_legal_kb
```

This script will:
1. Load rules from legal_rules.json
2. Generate embeddings using Gemini gemini-embedding-001 (3072 dimensions)
3. Insert rules into the legal_rules table
4. Skip duplicates (idempotent operation)

## Maintenance

For production deployments:
- Update this file with actual data sources and licensing information
- Document update procedures and schedules
- Include contact information for legal counsel or data providers
- Add version tracking and change logs
