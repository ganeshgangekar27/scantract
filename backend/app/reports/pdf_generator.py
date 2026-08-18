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
    
    # Build HTML sections
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contract Risk Report - {escape_html(report.filename)}</title>
</head>
<body>
    <!-- Cover Page -->
    <div class="cover-page">
        <h1>Contract Risk Report</h1>
        <h2>{escape_html(report.filename)}</h2>
        <p class="date">Upload Date: {report.upload_date.strftime('%B %d, %Y')}</p>
        <div class="risk-badge {report.risk_summary.overall_risk_level}">
            Overall Risk: {report.risk_summary.overall_risk_level.upper()}
        </div>
    </div>
    
    <!-- Risk Summary Section -->
    <div class="section">
        <h2>Risk Summary</h2>
        <table class="summary-table">
            <tr>
                <th>Metric</th>
                <th>Count</th>
            </tr>
            <tr>
                <td>Total Clauses</td>
                <td>{report.risk_summary.total_clauses}</td>
            </tr>
            <tr>
                <td>Risky Clauses</td>
                <td>{report.risk_summary.risky_clauses_count}</td>
            </tr>
            <tr>
                <td>Missing Clauses</td>
                <td>{report.risk_summary.missing_clauses_count}</td>
            </tr>
            <tr>
                <td>High Severity</td>
                <td class="severity-high">{report.risk_summary.high_severity_count}</td>
            </tr>
            <tr>
                <td>Medium Severity</td>
                <td class="severity-medium">{report.risk_summary.medium_severity_count}</td>
            </tr>
            <tr>
                <td>Low Severity</td>
                <td class="severity-low">{report.risk_summary.low_severity_count}</td>
            </tr>
        </table>
    </div>
    """
    
    # Risky Clauses Section
    if report.risky_clauses:
        html += """
    <div class="section">
        <h2>Risky Clauses</h2>
        """
        for risky in report.risky_clauses:
            html += f"""
        <div class="clause-box">
            <div class="clause-header">
                <span class="clause-number">Clause {escape_html(risky.clause_number)}</span>
                <span class="risk-badge {risky.severity}">{risky.severity.upper()}</span>
            </div>
            <p class="clause-text">{escape_html(risky.clause_text)}</p>
            <div class="risk-details">
                <h4>Risk Assessment</h4>
                <p><strong>Reason:</strong> {escape_html(risky.reason)}</p>
                <p><strong>Explanation:</strong> {escape_html(risky.explanation)}</p>
                <p class="citation"><strong>Legal Citation:</strong> {escape_html(risky.formatted_citation)}</p>
            </div>
        </div>
        """
        html += "</div>"
    
    # Missing Clauses Section
    if report.missing_clauses:
        html += """
    <div class="section">
        <h2>Missing Clauses</h2>
        """
        for missing in report.missing_clauses:
            html += f"""
        <div class="clause-box">
            <div class="clause-header">
                <span class="clause-number">Expected: {escape_html(missing.expected_clause_type)}</span>
                <span class="risk-badge {missing.severity}">{missing.severity.upper()}</span>
            </div>
            <div class="risk-details">
                <p><strong>Reason:</strong> {escape_html(missing.reason)}</p>
                <p><strong>Explanation:</strong> {escape_html(missing.explanation)}</p>
                <p class="citation"><strong>Legal Citation:</strong> {escape_html(missing.formatted_citation)}</p>
            </div>
        </div>
        """
        html += "</div>"
    
    # Legal References Appendix
    if report.legal_references:
        html += """
    <div class="section">
        <h2>Legal References</h2>
        <table class="references-table">
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
    body {
        font-family: Arial, sans-serif;
        margin: 2cm;
        color: #333;
    }
    
    h1 {
        font-size: 32px;
        margin-bottom: 16px;
    }
    
    h2 {
        font-size: 24px;
        margin-top: 24px;
        margin-bottom: 16px;
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 8px;
    }
    
    h4 {
        font-size: 16px;
        margin-top: 12px;
        margin-bottom: 8px;
        color: #555;
    }
    
    /* Cover Page */
    .cover-page {
        text-align: center;
        page-break-after: always;
        padding-top: 100px;
    }
    
    .cover-page h1 {
        color: #2c3e50;
    }
    
    .cover-page h2 {
        color: #34495e;
        border: none;
    }
    
    .cover-page .date {
        font-size: 18px;
        color: #7f8c8d;
        margin: 24px 0;
    }
    
    /* Risk Badges */
    .risk-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 14px;
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
    
    /* Tables */
    .summary-table,
    .references-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }
    
    .summary-table th,
    .summary-table td,
    .references-table th,
    .references-table td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
    }
    
    .summary-table th,
    .references-table th {
        background: #3498db;
        color: white;
        font-weight: bold;
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
    
    /* Clause Boxes */
    .clause-box {
        border: 1px solid #bdc3c7;
        padding: 16px;
        margin: 16px 0;
        background: #f8f9fa;
        page-break-inside: avoid;
    }
    
    .clause-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    
    .clause-number {
        font-weight: bold;
        font-size: 16px;
        color: #2c3e50;
    }
    
    .clause-text {
        background: white;
        padding: 12px;
        border-left: 4px solid #3498db;
        margin: 12px 0;
        font-family: Georgia, serif;
        line-height: 1.6;
    }
    
    .risk-details {
        margin-top: 12px;
    }
    
    .risk-details p {
        margin: 8px 0;
        line-height: 1.5;
    }
    
    /* Citations */
    .citation {
        font-family: 'Courier New', monospace;
        background: #ecf0f1;
        padding: 4px 8px;
        border-radius: 3px;
        font-size: 13px;
    }
    
    /* Sections */
    .section {
        margin-bottom: 32px;
    }
    """
