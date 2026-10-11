import { useState, useEffect, useRef } from 'react';
import { useReveal } from '../../hooks/useReveal';

type ContractType = 'rental' | 'freelance';

const DEMO_DATA = {
  rental: {
    steps: ['Upload', 'Clause extraction', 'Risk check', 'Report'],
    riskScore: 7,
    findings: [
      {
        title: 'Excessive Security Deposit',
        severity: 'high' as const,
        description: '6-month deposit exceeds standard 2-3 month limit',
      },
      {
        title: 'Lock-in Period Missing',
        severity: 'medium' as const,
        description: 'No minimum notice period specified for termination',
      },
      {
        title: 'Maintenance Clause Unclear',
        severity: 'low' as const,
        description: 'Responsibility for repairs not explicitly defined',
      },
    ],
  },
  freelance: {
    steps: ['Upload', 'Clause extraction', 'Risk check', 'Report'],
    riskScore: 5,
    findings: [
      {
        title: 'Payment Terms Vague',
        severity: 'high' as const,
        description: 'No specific payment schedule or milestones defined',
      },
      {
        title: 'IP Rights Not Transferred',
        severity: 'medium' as const,
        description: 'Intellectual property ownership remains with contractor',
      },
      {
        title: 'Scope Change Process Missing',
        severity: 'low' as const,
        description: 'No procedure for handling additional work requests',
      },
    ],
  },
};

export function InteractiveDemo() {
  const [activeTab, setActiveTab] = useState<ContractType>('rental');
  const [currentStep, setCurrentStep] = useState(0);
  const [riskCount, setRiskCount] = useState(0);
  const [visibleFindings, setVisibleFindings] = useState(0);
  const [hasAnimated, setHasAnimated] = useState(false);
  const sectionRef = useReveal<HTMLDivElement>();
  const animationRef = useRef<number | undefined>(undefined);

  const data = DEMO_DATA[activeTab];

  useEffect(() => {
    const element = sectionRef.current;
    if (!element) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          startAnimation(prefersReducedMotion);
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasAnimated]);

  const startAnimation = (immediate: boolean) => {
    if (immediate) {
      setCurrentStep(data.steps.length - 1);
      setRiskCount(data.riskScore);
      setVisibleFindings(data.findings.length);
      return;
    }

    let stepIndex = 0;
    const stepInterval = setInterval(() => {
      if (stepIndex < data.steps.length) {
        setCurrentStep(stepIndex);
        stepIndex++;
      } else {
        clearInterval(stepInterval);
        animateRiskCount();
      }
    }, 600);
  };

  const animateRiskCount = () => {
    const duration = 1000;
    const start = performance.now();
    const targetScore = data.riskScore;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - start;
      const progress = Math.min(elapsed / duration, 1);
      const current = Math.floor(progress * targetScore);
      setRiskCount(current);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        animateFindings();
      }
    };

    animationRef.current = requestAnimationFrame(animate);
  };

  const animateFindings = () => {
    let findingIndex = 0;
    const findingInterval = setInterval(() => {
      if (findingIndex < data.findings.length) {
        setVisibleFindings(findingIndex + 1);
        findingIndex++;
      } else {
        clearInterval(findingInterval);
      }
    }, 300);
  };

  const handleTabClick = (tab: ContractType) => {
    if (tab === activeTab) return;
    
    setActiveTab(tab);
    setCurrentStep(0);
    setRiskCount(0);
    setVisibleFindings(0);
    setHasAnimated(false);
  };

  const getSeverityColor = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high':
        return 'bg-severity-high-bg text-severity-high border-severity-high-border';
      case 'medium':
        return 'bg-severity-medium-bg text-severity-medium border-severity-medium-border';
      case 'low':
        return 'bg-severity-low-bg text-severity-low border-severity-low-border';
    }
  };

  return (
    <section ref={sectionRef} className="reveal bg-surface py-20">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary mb-4">
            See it in action
          </h2>
          <p className="text-lg text-text-secondary">
            Watch how ScanTract analyzes contracts in real-time
          </p>
        </div>

        {/* Tabs */}
        <div
          className="flex justify-center gap-4 mb-8"
          role="tablist"
          aria-label="Contract type"
        >
          <button
            role="tab"
            aria-selected={activeTab === 'rental'}
            aria-controls="rental-panel"
            className={`px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'rental'
                ? 'bg-primary text-white'
                : 'bg-background text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => handleTabClick('rental')}
          >
            Rental agreement
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'freelance'}
            aria-controls="freelance-panel"
            className={`px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === 'freelance'
                ? 'bg-primary text-white'
                : 'bg-background text-text-secondary hover:text-text-primary'
            }`}
            onClick={() => handleTabClick('freelance')}
          >
            Freelance contract
          </button>
        </div>

        {/* Demo Panel */}
        <div
          id={`${activeTab}-panel`}
          role="tabpanel"
          className="bg-background rounded-xl p-8 border border-border"
        >
          <div className="grid md:grid-cols-2 gap-8">
            {/* Pipeline Steps */}
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                Processing Pipeline
              </h3>
              <div className="space-y-3">
                {data.steps.map((step, index) => (
                  <div
                    key={step}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                      index <= currentStep
                        ? 'bg-primary/10 border border-primary/30'
                        : 'bg-surface border border-border'
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                        index < currentStep
                          ? 'bg-primary text-white'
                          : index === currentStep
                          ? 'bg-primary text-white animate-pulse'
                          : 'bg-border text-text-secondary'
                      }`}
                    >
                      {index < currentStep ? '✓' : index + 1}
                    </div>
                    <span
                      className={`font-medium ${
                        index <= currentStep ? 'text-text-primary' : 'text-text-secondary'
                      }`}
                    >
                      {step}
                    </span>
                  </div>
                ))}
              </div>

              {/* Risk Score */}
              <div className="mt-6 p-4 bg-surface rounded-lg border border-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-text-secondary">
                    Risk Score
                  </span>
                  <span className="text-3xl font-bold text-severity-high">
                    {riskCount}/10
                  </span>
                </div>
                <div className="w-full bg-border rounded-full h-2">
                  <div
                    className="bg-severity-high rounded-full h-2 transition-all duration-500"
                    style={{ width: `${(riskCount / 10) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Findings */}
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                Key Findings
              </h3>
              <div className="space-y-3">
                {data.findings.map((finding, index) => (
                  <div
                    key={finding.title}
                    className={`p-4 bg-surface rounded-lg border border-border transition-all duration-500 ${
                      index < visibleFindings
                        ? 'opacity-100 translate-y-0'
                        : 'opacity-0 translate-y-4'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-text-primary">
                        {finding.title}
                      </h4>
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(
                          finding.severity
                        )}`}
                      >
                        {finding.severity}
                      </span>
                    </div>
                    <p className="text-sm text-text-secondary">
                      {finding.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sample Data Label */}
          <div className="mt-6 pt-4 border-t border-border text-center">
            <p className="text-xs text-text-secondary italic">
              Sample data for illustration
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
