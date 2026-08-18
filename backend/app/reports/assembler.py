"""
Contract report assembly logic.

Fetches contract data, clauses, and risk findings from the database,
then assembles them into a comprehensive ContractReport.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List
from collections import defaultdict
import logging

from ..db.models import Contract, Clause, RiskFinding
from ..llm.generate_explanations import generate_all_explanations
from .models import (
    ContractReport,
    ClauseWithRisk,
    RiskyClauseReport,
    MissingClauseReport,
    RiskSummary,
    LegalReference
)

logger = logging.getLogger(__name__)


async def assemble_contract_report(
    contract_id: int,
    db: AsyncSession
) -> ContractReport:
    """
    Assemble complete report for a contract.
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        ContractReport with all clauses, risks, and references
    
    Raises:
        ValueError: If contract not found or processing incomplete
    """
    # Step 1: Fetch contract from database
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise ValueError("Contract not found")
    
    if contract.processing_status != 'complete':
        raise ValueError("Contract processing not complete")
    
    # Step 2: Ensure all explanations are cached
    await generate_all_explanations(contract_id, db)
    
    # Step 3: Fetch all clauses for the contract
    result = await db.execute(
        select(Clause)
        .where(Clause.contract_id == contract_id)
        .order_by(Clause.clause_id)
    )
    clauses = result.scalars().all()
    
    # Step 4: Fetch all risk findings with cached explanations
    result = await db.execute(
        select(RiskFinding)
        .where(RiskFinding.contract_id == contract_id)
    )
    findings = result.scalars().all()
    
    # Step 5: Build risk map (clause_id -> list of findings)
    risk_map: Dict[int, List[RiskFinding]] = defaultdict(list)
    for finding in findings:
        if finding.clause_id is not None:
            risk_map[finding.clause_id].append(finding)
    
    # Step 6: Build ClauseWithRisk objects
    all_clauses = []
    for clause in clauses:
        clause_risks = risk_map.get(clause.id, [])
        has_risk = len(clause_risks) > 0
        
        # Determine highest severity for this clause
        risk_severity = None
        risk_reason = None
        if has_risk:
            # Priority: high > medium > low
            severity_order = {"high": 3, "medium": 2, "low": 1}
            highest_risk = max(clause_risks, key=lambda f: severity_order.get(f.severity, 0))
            risk_severity = highest_risk.severity
            risk_reason = highest_risk.reason
        
        all_clauses.append(ClauseWithRisk(
            clause_id=clause.id,
            clause_number=clause.clause_id,
            clause_text=clause.text,
            has_risk=has_risk,
            risk_severity=risk_severity,
            risk_reason=risk_reason
        ))
    
    # Step 7: Build RiskyClauseReport and MissingClauseReport lists
    risky_clauses = []
    missing_clauses = []
    
    for finding in findings:
        if finding.finding_type == "risky_clause" and finding.clause_id is not None:
            # Fetch clause details
            clause = next((c for c in clauses if c.id == finding.clause_id), None)
            if clause:
                risky_clauses.append(RiskyClauseReport(
                    finding_id=str(finding.id),
                    clause_id=finding.clause_id,
                    clause_number=clause.clause_id,
                    clause_text=clause.text,
                    severity=finding.severity,
                    reason=finding.reason,
                    explanation=finding.explanation or "Explanation pending...",
                    formatted_citation=finding.formatted_citation or ""
                ))
        elif finding.finding_type == "missing_clause":
            missing_clauses.append(MissingClauseReport(
                finding_id=str(finding.id),
                expected_clause_type=finding.expected_clause_type or "unknown",
                severity=finding.severity,
                reason=finding.reason,
                explanation=finding.explanation or "Explanation pending...",
                formatted_citation=finding.formatted_citation or ""
            ))
    
    # Sort risky clauses by severity (high first), then clause_number
    severity_order = {"high": 3, "medium": 2, "low": 1}
    risky_clauses.sort(
        key=lambda r: (-severity_order.get(r.severity, 0), r.clause_number)
    )
    
    # Sort missing clauses by severity (high first)
    missing_clauses.sort(
        key=lambda m: -severity_order.get(m.severity, 0)
    )
    
    # Step 8: Compute RiskSummary
    high_count = sum(1 for f in findings if f.severity == "high")
    medium_count = sum(1 for f in findings if f.severity == "medium")
    low_count = sum(1 for f in findings if f.severity == "low")
    
    # Determine overall risk level
    if high_count > 0:
        overall_risk = "high"
    elif medium_count > 0:
        overall_risk = "medium"
    elif low_count > 0:
        overall_risk = "low"
    else:
        overall_risk = "none"
    
    risk_summary = RiskSummary(
        total_clauses=len(clauses),
        risky_clauses_count=len(risky_clauses),
        missing_clauses_count=len(missing_clauses),
        high_severity_count=high_count,
        medium_severity_count=medium_count,
        low_severity_count=low_count,
        overall_risk_level=overall_risk
    )
    
    # Step 9: Deduplicate legal references
    citation_counts: Dict[str, int] = defaultdict(int)
    for finding in findings:
        if finding.formatted_citation:
            citation_counts[finding.formatted_citation] += 1
    
    legal_references = [
        LegalReference(citation=citation, usage_count=count)
        for citation, count in citation_counts.items()
    ]
    
    # Sort by usage_count desc, then alphabetically
    legal_references.sort(key=lambda ref: (-ref.usage_count, ref.citation))
    
    # Step 10: Return ContractReport
    return ContractReport(
        contract_id=contract.id,
        filename=contract.filename,
        upload_date=contract.upload_date,
        all_clauses=all_clauses,
        risky_clauses=risky_clauses,
        missing_clauses=missing_clauses,
        risk_summary=risk_summary,
        legal_references=legal_references
    )
