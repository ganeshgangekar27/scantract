import { useReveal } from '../../hooks/useReveal';

export function Features() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <section ref={ref} className="reveal max-w-7xl mx-auto px-6 py-20">
      <h2 className="text-3xl md:text-4xl font-bold text-center text-text-primary mb-12">
        Contract analysis made simple
      </h2>
      <div className="grid md:grid-cols-3 gap-8">
        <div className="feature-card bg-surface border border-border rounded-xl p-8 hover-lift hover-glow transition-all">
          <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-text-primary mb-2">Upload any contract</h3>
          <p className="text-text-secondary">
            PDF, DOCX, or scanned documents. Our system extracts text and clauses automatically
          </p>
        </div>

        <div className="feature-card bg-surface border border-border rounded-xl p-8 hover-lift hover-glow transition-all">
          <div className="w-12 h-12 bg-severity-high/10 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-severity-high" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-text-primary mb-2">Risk findings with reasons</h3>
          <p className="text-text-secondary">
            Every flagged clause includes severity level, explanation, and legal reference
          </p>
        </div>

        <div className="feature-card bg-surface border border-border rounded-xl p-8 hover-lift hover-glow transition-all">
          <div className="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-text-primary mb-2">Missing-clause check</h3>
          <p className="text-text-secondary">
            Identifies standard protections missing from your contract based on Indian rental norms
          </p>
        </div>
      </div>
    </section>
  );
}
