import { Link } from 'react-router-dom';

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* Gradient Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#1e293b] via-primary to-primary-dark">
        {/* Animated Blobs */}
        <div className="absolute top-20 left-10 w-72 h-72 bg-accent/30 rounded-full blur-3xl animate-blob"></div>
        <div className="absolute top-40 right-20 w-96 h-96 bg-primary/40 rounded-full blur-3xl animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-20 left-1/3 w-80 h-80 bg-accent/20 rounded-full blur-3xl animate-blob animation-delay-4000"></div>
        
        {/* Grid Overlay */}
        <div className="absolute inset-0 bg-grid opacity-10"></div>
      </div>

      <div className="relative max-w-7xl mx-auto px-6 py-20 md:py-32">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-6 fade-up">
            <h1 className="text-5xl md:text-6xl font-bold text-white leading-tight">
              Analyze rental contracts in{' '}
              <span className="text-accent">seconds</span>
            </h1>
            <p className="text-xl text-white/80">
              Upload your contract and get instant risk analysis backed by Indian legal norms
            </p>
            <div className="flex flex-col sm:flex-row gap-4 pt-4">
              <Link
                to="/signup"
                className="px-8 py-3 bg-white text-primary rounded-lg hover:bg-white/90 transition-all hover-lift text-lg font-medium text-center"
              >
                Get started free
              </Link>
              <Link
                to="/login"
                className="px-8 py-3 border-2 border-white/30 text-white rounded-lg hover:border-white hover:bg-white/10 transition-all hover-lift text-lg font-medium text-center"
              >
                See how it works
              </Link>
            </div>
          </div>

          {/* App Preview Card */}
          <div className="relative float-animation">
            <div className="bg-white rounded-xl shadow-2xl overflow-hidden">
              {/* Browser Frame */}
              <div className="bg-surface border-b border-border px-4 py-3 flex items-center gap-2">
                <div className="flex gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
                  <div className="w-3 h-3 rounded-full bg-[#27c93f]"></div>
                </div>
                <div className="flex-1 ml-4 bg-background rounded px-3 py-1 text-xs text-text-secondary">
                  scantract.app
                </div>
              </div>
              
              {/* App Preview Content */}
              <div className="p-6 bg-background">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-3 h-3 rounded-full bg-severity-high animate-pulse-slow"></div>
                  <span className="text-sm font-medium text-text-secondary">Risk Detection</span>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-text-primary font-medium">Security Deposit</span>
                    <span className="px-3 py-1 bg-severity-high-bg text-severity-high border border-severity-high-border rounded text-sm font-medium">
                      High
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary">
                    Clause allows 6-month deposit, exceeding typical 2-3 month standard
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
        </div>
      </div>
    </section>
  );
}
