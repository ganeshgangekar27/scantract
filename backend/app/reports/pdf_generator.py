"""
PDF report generation using weasyprint.

Converts ContractReport data into a formatted PDF document.
"""

from io import BytesIO
import logging

from .models import ContractReport

logger = logging.getLogger(__name__)

# Try to import weasyprint - may fail on Windows without GTK libraries
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (OSError, ImportError) as e:
    logger.warning(f"weasyprint not available: {e}")
    WEASYPRINT_AVAILABLE = False


def generate_pdf_report(report: ContractReport) -> bytes:
    """
    Generate PDF report from ContractReport data.
    
    Args:
        report: ContractReport with all data assembled
    
    Returns:
        bytes: PDF file content
        
    Raises:
        RuntimeError: If weasyprint is not available (missing GTK libraries on Windows)
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError(
            "weasyprint is not available. On Windows, GTK libraries are required. "
            "See: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows"
        )
    
    # Build HTML content
    html_content = _build_html(report)
    
    # Build CSS styles
    css_styles = _build_css()
    
    # Generate PDF using weasyprint
    html = HTML(string=html_content)
    css = CSS(string=css_styles)
    pdf_bytes = BytesIO()
    html.write_pdf(pdf_bytes, stylesheets=[css])
    
    return pdf_bytes.getvalue()


def _truncate(text: str, max_chars: int) -> str:
    """
    Truncate text at word boundary and append ellipsis if cut.
    
    Args:
        text: Text to truncate (can be None or empty)
        max_chars: Maximum character count
        
    Returns:
        Truncated text with ellipsis if cut, or original text if shorter
    """
    if not text:
        return ""
    
    if len(text) <= max_chars:
        return text
    
    # Cut at word boundary
    truncated = text[:max_chars].rsplit(' ', 1)[0]
    return truncated + "…"


def _build_html(report: ContractReport) -> str:
    """Build HTML content for the PDF report."""
    # Escape HTML special characters
    def escape_html(text: str) -> str:
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))
    
    # Calculate severity bar widths (proportional to counts)
    total_severity = (report.risk_summary.high_severity_count + 
                      report.risk_summary.medium_severity_count + 
                      report.risk_summary.low_severity_count)
    
    if total_severity > 0:
        high_pct = (report.risk_summary.high_severity_count / total_severity) * 100
        medium_pct = (report.risk_summary.medium_severity_count / total_severity) * 100
        low_pct = (report.risk_summary.low_severity_count / total_severity) * 100
        severity_bar_html = f"""
        <div class="severity-bar">
            <div class="severity-segment high" style="width: {high_pct}%"></div>
            <div class="severity-segment medium" style="width: {medium_pct}%"></div>
            <div class="severity-segment low" style="width: {low_pct}%"></div>
        </div>
        """
    else:
        severity_bar_html = '<div class="severity-bar"><div class="severity-segment neutral" style="width: 100%"></div></div>'
    
    # Build HTML sections - compact header on page 1
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contract Risk Report - {escape_html(report.filename)}</title>
</head>
<body>
    <!-- Compact Header (no separate cover page) -->
    <div class="compact-header">
        <h1>Contract Risk Report</h1>
        <p class="filename">{escape_html(report.filename)}</p>
        <p class="date">Upload Date: {report.upload_date.strftime('%B %d, %Y')}</p>
        <div class="risk-badge {report.risk_summary.overall_risk_level}">
            Overall Risk: {report.risk_summary.overall_risk_level.upper()}
        </div>
    </div>
    
    <!-- Risk Summary Section (compact) -->
    <div class="section">
        <h2>Risk Summary</h2>
        <table class="summary-table compact">
            <tr>
                <th>Total Clauses</th>
                <th>Risky Clauses</th>
                <th>Missing Clauses</th>
                <th>High</th>
                <th>Medium</th>
                <th>Low</th>
            </tr>
            <tr>
                <td>{report.risk_summary.total_clauses}</td>
                <td>{report.risk_summary.risky_clauses_count}</td>
                <td>{report.risk_summary.missing_clauses_count}</td>
                <td class="severity-high">{report.risk_summary.high_severity_count}</td>
                <td class="severity-medium">{report.risk_summary.medium_severity_count}</td>
                <td class="severity-low">{report.risk_summary.low_severity_count}</td>
            </tr>
        </table>
        {severity_bar_html}
    </div>
    """
    
    # Top Risks section (first 5 risky clauses)
    if report.risky_clauses:
        html += """
    <div class="section">
        <h2>Top Risks</h2>
        """
        for risky in report.risky_clauses[:5]:
            html += f"""
        <div class="top-risk-item">
            <span class="risk-badge {risky.severity}">{risky.severity.upper()}</span>
            <span class="clause-number">Clause {escape_html(risky.clause_number)}</span>
            <span class="risk-reason">{escape_html(_truncate(risky.reason, 140))}</span>
        </div>
        """
        html += "</div>"
    
    # Risky Clauses Section (compact table)
    if report.risky_clauses:
        html += """
    <div class="section">
        <h2>Risky Clauses</h2>
        <table class="risky-clauses-table">
            <tr>
                <th>Clause #</th>
                <th>Severity</th>
                <th>Clause Text</th>
                <th>Why It Matters</th>
            </tr>
        """
        for risky in report.risky_clauses:
            html += f"""
            <tr>
                <td class="clause-number">{escape_html(risky.clause_number)}</td>
                <td><span class="risk-badge {risky.severity}">{risky.severity.upper()}</span></td>
                <td class="clause-text-cell">{escape_html(_truncate(risky.clause_text, 160))}</td>
                <td class="explanation-cell">{escape_html(_truncate(risky.explanation, 240))}</td>
            </tr>
            """
        html += """
        </table>
    </div>
        """
    
    # Missing Clauses Section (compact table)
    if report.missing_clauses:
        html += """
    <div class="section">
        <h2>Missing Clauses</h2>
        <table class="missing-clauses-table">
            <tr>
                <th>Expected Clause</th>
                <th>Severity</th>
                <th>Why It Matters</th>
            </tr>
        """
        for missing in report.missing_clauses:
            html += f"""
            <tr>
                <td class="clause-type">{escape_html(missing.expected_clause_type)}</td>
                <td><span class="risk-badge {missing.severity}">{missing.severity.upper()}</span></td>
                <td class="explanation-cell">{escape_html(_truncate(missing.explanation, 240))}</td>
            </tr>
            """
        html += """
        </table>
    </div>
        """
    
    # Legal References Appendix (compact)
    if report.legal_references:
        html += """
    <div class="section">
        <h2>Legal References</h2>
        <table class="references-table compact">
            <tr>
                <th>Citation</th>
                <th>Usage Count</th>
            </tr>
        """
        for ref in report.legal_references:
            html += f"""
            <tr>
                <td class="citation">{escape_html(ref.citation)}</td>
                <td>{ref.usage_count}</td>
            </tr>
            """
        html += """
        </table>
    </div>
        """
    
    html += """
</body>
</html>
    """
    
    return html


def _build_css() -> str:
    """Build CSS styles for the PDF report."""
    return """
    @page {
        margin: 1.5cm;
        
        @bottom-center {
            content: "Page " counter(page) " of " counter(pages);
            font-size: 8pt;
            color: #666;
        }
        
        @bottom-right {
            content: "AI-generated analysis. Not legal advice.";
            font-size: 8pt;
            color: #999;
            font-style: italic;
        }
    }
    
    body {
        font-family: Arial, sans-serif;
        font-size: 10pt;
        color: #333;
        line-height: 1.4;
    }
    
    h1 {
        font-size: 20pt;
        margin: 0 0 8px 0;
        color: #2c3e50;
    }
    
    h2 {
        font-size: 14pt;
        margin: 16px 0 8px 0;
        color: #2c3e50;
        border-bottom: 1px solid #3498db;
        padding-bottom: 4px;
    }
    
    /* Compact Header (replaces cover page) */
    .compact-header {
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 2px solid #3498db;
    }
    
    .compact-header .filename {
        font-size: 12pt;
        font-weight: bold;
        margin: 4px 0;
        color: #34495e;
    }
    
    .compact-header .date {
        font-size: 9pt;
        color: #7f8c8d;
        margin: 4px 0 8px 0;
    }
    
    /* Risk Badges */
    .risk-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 3px;
        font-weight: bold;
        font-size: 8pt;
    }
    
    .risk-badge.high {
        background: #fee;
        color: #c00;
        border: 1px solid #c00;
    }
    
    .risk-badge.medium {
        background: #ffe;
        color: #c60;
        border: 1px solid #c60;
    }
    
    .risk-badge.low {
        background: #ffa;
        color: #960;
        border: 1px solid #960;
    }
    
    .risk-badge.none {
        background: #efe;
        color: #060;
        border: 1px solid #060;
    }
    
    /* Severity Bar */
    .severity-bar {
        display: flex;
        height: 20px;
        margin: 12px 0;
        border-radius: 4px;
        overflow: hidden;
        border: 1px solid #ddd;
    }
    
    .severity-segment {
        height: 100%;
    }
    
    .severity-segment.high {
        background: #dc3545;
    }
    
    .severity-segment.medium {
        background: #ffc107;
    }
    
    .severity-segment.low {
        background: #ffeb3b;
    }
    
    .severity-segment.neutral {
        background: #ccc;
    }
    
    /* Tables - Compact */
    .summary-table.compact,
    .references-table.compact,
    .risky-clauses-table,
    .missing-clauses-table {
        width: 100%;
        border-collapse: collapse;
        margin: 8px 0;
        font-size: 9pt;
    }
    
    .summary-table.compact th,
    .summary-table.compact td,
    .references-table.compact th,
    .references-table.compact td,
    .risky-clauses-table th,
    .risky-clauses-table td,
    .missing-clauses-table th,
    .missing-clauses-table td {
        border: 1px solid #ddd;
        padding: 6px 8px;
        text-align: left;
    }
    
    .summary-table.compact th,
    .references-table.compact th,
    .risky-clauses-table th,
    .missing-clauses-table th {
        background: #3498db;
        color: white;
        font-weight: bold;
        font-size: 9pt;
    }
    
    .risky-clauses-table tr,
    .missing-clauses-table tr {
        page-break-inside: avoid;
    }
    
    .risky-clauses-table .clause-number,
    .missing-clauses-table .clause-type {
        font-weight: bold;
        white-space: nowrap;
    }
    
    .risky-clauses-table .clause-text-cell,
    .risky-clauses-table .explanation-cell,
    .missing-clauses-table .explanation-cell {
        font-size: 8pt;
        line-height: 1.3;
    }
    
    .severity-high {
        color: #c00;
        font-weight: bold;
    }
    
    .severity-medium {
        color: #c60;
        font-weight: bold;
    }
    
    .severity-low {
        color: #960;
        font-weight: bold;
    }
    
    /* Top Risks Items */
    .top-risk-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 0;
        border-bottom: 1px solid #eee;
    }
    
    .top-risk-item .clause-number {
        font-weight: bold;
        font-size: 9pt;
        min-width: 80px;
    }
    
    .top-risk-item .risk-reason {
        font-size: 9pt;
        color: #555;
    }
    
    /* Citations */
    .citation {
        font-family: 'Courier New', monospace;
        font-size: 8pt;
    }
    
    /* Sections */
    .section {
        margin-bottom: 16px;
    }
    """
