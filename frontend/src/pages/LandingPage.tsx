import { Link } from 'react-router-dom';
import { useReveal } from '../hooks/useReveal';

export function LandingPage() {
  const heroRef = useReveal<HTMLDivElement>();
  const featuresRef = useReveal<HTMLDivElement>();
  const howItWorksRef = useReveal<HTMLDivElement>();
  const ctaRef = useReveal<HTMLDivElement>();

  return (
    <div className="min-h-screen bg-background">
      {/* Sticky Navigation */}
      <nav className="sticky top-0 z-50 bg-surface/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="text-2xl font-bold text-primary gradient-text">ScanTract</div>
          <div className="flex gap-4">
            <Link
              to="/login"
              className="px-6 py-2 text-text-primary hover:text-primary transition-colors"
            >
              Log in
            </Link>
            <Link
              to="/signup"
              className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-all hover-lift"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section ref={heroRef} className="reveal max-w-7xl mx-auto px-6 py-20 md:py-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-6 fade-up">
            <h1 className="text-5xl md:text-6xl font-bold text-text-primary leading-tight">
              Analyze rental contracts in{' '}
              <span className="gradient-text">seconds</span>
            </h1>
            <p className="text-xl text-text-secondary">
              Upload your contract and get instant risk analysis backed by Indian legal norms
            </p>
            <div className="flex gap-4 pt-4">
              <Link
                to="/signup"
                className="px-8 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-all hover-lift text-lg font-medium"
              >
                Get started free
              </Link>
              <Link
                to="/login"
                className="px-8 py-3 border-2 border-border text-text-primary rounded-lg hover:border-primary hover:text-primary transition-all hover-lift text-lg font-medium"
              >
                See how it works
              </Link>
            </div>
          </div>

          {/* Decorative Risk Ring Card */}
          <div className="relative">
            <div className="risk-card float-animation bg-surface border border-border rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-3 h-3 rounded-full bg-severity-high animate-pulse-slow"></div>
                <span className="text-sm font-medium text-text-secondary">Risk Detection</span>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-text-primary">Security Deposit</span>
                  <span className="px-3 py-1 bg-severity-high-bg text-severity-high border border-severity-high-border rounded text-sm font-medium">
                    High
                  </span>
                </div>
                <p className="text-sm text-text-secondary">
                  Clause allows 6-month deposit, exceeding typical 2-3 month standard under rental agreements
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-border">
                <div className="flex items-center gap-2 text-xs text-text-secondary">
                  <div className="w-4 h-4 rounded-full bg-accent/20 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-accent"></div>
                  </div>
                  <span>Referenced: Model Tenancy Act 2021</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section ref={featuresRef} className="reveal bg-surface py-20">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center text-text-primary mb-12">
            Contract analysis made simple
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="feature-card bg-background border border-border rounded-xl p-8 hover-lift transition-all">
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

            <div className="feature-card bg-background border border-border rounded-xl p-8 hover-lift transition-all">
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

            <div className="feature-card bg-background border border-border rounded-xl p-8 hover-lift transition-all">
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
        </div>
      </section>

      {/* How It Works */}
      <section ref={howItWorksRef} className="reveal max-w-7xl mx-auto px-6 py-20">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-text-primary mb-12">
          How it works
        </h2>
        <div className="grid md:grid-cols-3 gap-12">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto">
              1
            </div>
            <h3 className="text-xl font-semibold text-text-primary">Upload</h3>
            <p className="text-text-secondary">
              Drop your rental or freelance contract. Supports PDF, DOCX, and scanned images
            </p>
          </div>

          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto">
              2
            </div>
            <h3 className="text-xl font-semibold text-text-primary">AI analysis</h3>
            <p className="text-text-secondary">
              Our system compares clauses against Indian legal rules and reference contracts
            </p>
          </div>

          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto">
              3
            </div>
            <h3 className="text-xl font-semibold text-text-primary">Review report</h3>
            <p className="text-text-secondary">
              Get a detailed breakdown of risks, missing clauses, and plain-language explanations
            </p>
          </div>
        </div>
      </section>

      {/* Disclaimer Strip */}
      <div className="bg-severity-medium-bg border-y border-severity-medium-border py-4">
        <div className="max-w-7xl mx-auto px-6">
          <p className="text-center text-severity-medium text-sm">
            <strong>Important:</strong> Sample knowledge base, not legal advice. For informational purposes only. Consult a licensed attorney for legal guidance.
          </p>
        </div>
      </div>

      {/* Final CTA */}
      <section ref={ctaRef} className="reveal max-w-7xl mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-text-primary mb-6">
          Ready to analyze your contract?
        </h2>
        <p className="text-xl text-text-secondary mb-8">
          Join users who are reviewing their rental agreements with confidence
        </p>
        <Link
          to="/signup"
          className="inline-block px-10 py-4 bg-primary text-white rounded-lg hover:bg-primary-dark transition-all hover-lift text-lg font-medium"
        >
          Get started free
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-text-secondary">
            <span className="font-semibold text-text-primary">ScanTract</span> — Contract analysis for rental and freelance agreements
          </p>
        </div>
      </footer>

      <style>{`
        @keyframes fadeUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes float {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-10px);
          }
        }

        @keyframes gradientShift {
          0%, 100% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
        }

        @keyframes pulseSlow {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        .fade-up {
          animation: fadeUp 0.8s ease-out;
        }

        .float-animation {
          animation: float 3s ease-in-out infinite;
        }

        .gradient-text {
          background: linear-gradient(90deg, var(--color-primary), var(--color-accent), var(--color-primary));
          background-size: 200% auto;
          background-clip: text;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: gradientShift 3s ease infinite;
        }

        .animate-pulse-slow {
          animation: pulseSlow 2s ease-in-out infinite;
        }

        .hover-lift {
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .hover-lift:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 16px -4px rgba(15, 23, 42, 0.12);
        }

        .reveal {
          opacity: 0;
          transform: translateY(30px);
          transition: opacity 0.6s ease, transform 0.6s ease;
        }

        .reveal.visible {
          opacity: 1;
          transform: translateY(0);
        }

        @media (prefers-reduced-motion: reduce) {
          .fade-up,
          .float-animation,
          .gradient-text,
          .animate-pulse-slow,
          .reveal {
            animation: none;
          }

          .hover-lift:hover {
            transform: none;
          }

          .reveal {
            opacity: 1;
            transform: none;
          }
        }
      `}</style>
    </div>
  );
}
