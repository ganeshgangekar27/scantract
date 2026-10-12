import { Link } from 'react-router-dom';
import { useReveal } from '../hooks/useReveal';
import { Navigation } from '../components/landing/Navigation';
import { Hero } from '../components/landing/Hero';
import { InteractiveDemo } from '../components/landing/InteractiveDemo';
import { Features } from '../components/landing/Features';
import { HowItWorks } from '../components/landing/HowItWorks';
import { OptionalVideo } from '../components/landing/OptionalVideo';
import { FAQ } from '../components/landing/FAQ';

export function LandingPage() {
  const ctaRef = useReveal<HTMLDivElement>();

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <Hero />
      <InteractiveDemo />
      <Features />
      <HowItWorks />
      <OptionalVideo />
      <FAQ />

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
          <div className="mt-4 space-x-6">
            <Link to="/privacy" className="text-text-secondary hover:text-primary transition-colors">
              Privacy
            </Link>
            <Link to="/terms" className="text-text-secondary hover:text-primary transition-colors">
              Terms
            </Link>
          </div>
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

        @keyframes blob {
          0%, 100% {
            transform: translate(0, 0) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
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

        @keyframes drawLine {
          from {
            width: 0;
          }
          to {
            width: 66.666%;
          }
        }

        .fade-up {
          animation: fadeUp 0.8s ease-out;
        }

        .float-animation {
          animation: float 3s ease-in-out infinite;
        }

        .animate-blob {
          animation: blob 7s infinite;
        }

        .animation-delay-2000 {
          animation-delay: 2s;
        }

        .animation-delay-4000 {
          animation-delay: 4s;
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

        .hover-glow {
          position: relative;
        }

        .hover-glow:hover {
          border-color: var(--color-primary);
          box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
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

        .draw-line {
          animation: drawLine 1.5s ease-out forwards;
          animation-play-state: paused;
        }

        .reveal.visible .draw-line {
          animation-play-state: running;
        }

        .bg-grid {
          background-image: 
            linear-gradient(to right, rgba(255, 255, 255, 0.1) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
          background-size: 40px 40px;
        }

        @media (prefers-reduced-motion: reduce) {
          .fade-up,
          .float-animation,
          .animate-blob,
          .gradient-text,
          .animate-pulse-slow,
          .reveal,
          .draw-line {
            animation: none !important;
          }

          .hover-lift:hover {
            transform: none;
          }

          .reveal {
            opacity: 1;
            transform: none;
          }

          .draw-line {
            width: 66.666%;
          }
        }
      `}</style>
    </div>
  );
}
