import { useReveal } from '../../hooks/useReveal';

export function HowItWorks() {
  const ref = useReveal<HTMLDivElement>();

  return (
    <section ref={ref} className="reveal bg-surface py-20">
      <div className="max-w-7xl mx-auto px-6">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-text-primary mb-12">
          How it works
        </h2>
        <div className="relative">
          {/* Connecting Line */}
          <div className="hidden md:block absolute top-8 left-1/6 right-1/6 h-0.5 bg-border draw-line"></div>
          
          <div className="grid md:grid-cols-3 gap-12 relative">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto relative z-10 ring-4 ring-surface">
                1
              </div>
              <h3 className="text-xl font-semibold text-text-primary">Upload</h3>
              <p className="text-text-secondary">
                Drop your rental or freelance contract. Supports PDF, DOCX, and scanned images
              </p>
            </div>

            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto relative z-10 ring-4 ring-surface">
                2
              </div>
              <h3 className="text-xl font-semibold text-text-primary">AI analysis</h3>
              <p className="text-text-secondary">
                Our system compares clauses against Indian legal rules and reference contracts
              </p>
            </div>

            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto relative z-10 ring-4 ring-surface">
                3
              </div>
              <h3 className="text-xl font-semibold text-text-primary">Review report</h3>
              <p className="text-text-secondary">
                Get a detailed breakdown of risks, missing clauses, and plain-language explanations
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
