import { useState } from 'react';
import { useReveal } from '../../hooks/useReveal';

const FAQ_DATA = [
  {
    question: 'Is this legal advice?',
    answer: 'No, ScanTract is not a substitute for legal advice. We provide informational analysis based on a sample knowledge base of Indian legal norms and common contract patterns. For legal guidance on your specific situation, please consult a licensed attorney.',
  },
  {
    question: 'Where is my data stored and can I delete it?',
    answer: 'Your contracts and analysis are stored securely in your own account. You have full control over your data and can delete all your contracts and analysis at any time from the Settings page. We do not share your contract content with third parties.',
  },
  {
    question: 'How accurate is the risk detection?',
    answer: 'ScanTract uses a sample knowledge base and AI analysis, which means it can be wrong or miss important issues. The system is designed to highlight potential areas of concern, but it should not be relied upon as the sole method of contract review. Always verify findings with appropriate legal counsel.',
  },
  {
    question: 'What file types are supported?',
    answer: 'ScanTract accepts PDF and DOCX files up to 15MB. We also support scanned documents through OCR (optical character recognition), though scanned contracts may take slightly longer to process.',
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const ref = useReveal<HTMLDivElement>();

  const toggleItem = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section ref={ref} className="reveal max-w-4xl mx-auto px-6 py-20">
      <h2 className="text-3xl md:text-4xl font-bold text-center text-text-primary mb-12">
        Frequently asked questions
      </h2>
      <div className="space-y-4">
        {FAQ_DATA.map((item, index) => (
          <div
            key={index}
            className="bg-surface border border-border rounded-xl overflow-hidden"
          >
            <button
              className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-background transition-colors"
              onClick={() => toggleItem(index)}
              aria-expanded={openIndex === index}
              aria-controls={`faq-answer-${index}`}
            >
              <span className="font-semibold text-text-primary pr-4">
                {item.question}
              </span>
              <svg
                className={`w-5 h-5 text-text-secondary transition-transform flex-shrink-0 ${
                  openIndex === index ? 'rotate-180' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            {openIndex === index && (
              <div
                id={`faq-answer-${index}`}
                className="px-6 pb-4 text-text-secondary"
              >
                {item.answer}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
