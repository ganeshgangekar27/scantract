import { useState } from 'react';
import { answerFor } from '../lib/helpAnswers';

const topics = [
  { label: 'How to upload', query: 'upload' },
  { label: 'File types & limits', query: 'file type' },
  { label: 'Processing time', query: 'processing' },
  { label: 'Risk levels', query: 'risk' },
  { label: 'Clause cards', query: 'clause' },
  { label: 'Past contracts', query: 'past contracts' },
  { label: 'Failed contracts', query: 'failed' },
  { label: 'Delete data', query: 'delete' },
  { label: 'Legal disclaimer', query: 'legal advice' },
];

export function HelpBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [answer, setAnswer] = useState('');

  const handleTopicClick = (query: string) => {
    const result = answerFor(query);
    setAnswer(result.answer);
    setInput('');
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInput(value);
    if (value.trim()) {
      const result = answerFor(value);
      setAnswer(result.answer);
    } else {
      setAnswer('');
    }
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        data-testid="help-bot-button"
        aria-label="Open help"
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-br from-primary to-accent rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-110 flex items-center justify-center text-white z-50"
      >
        {isOpen ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )}
      </button>

      {/* Help panel */}
      {isOpen && (
        <div
          data-testid="help-bot-panel"
          className="fixed bottom-24 right-6 w-96 max-h-[600px] bg-white dark:bg-gray-800 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-700 z-50 flex flex-col"
        >
          {/* Header */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white">Help</h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              data-testid="help-bot-close"
              aria-label="Close help"
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {/* Search input */}
            <div className="mb-4">
              <label htmlFor="help-search" className="sr-only">Search help topics</label>
              <input
                id="help-search"
                type="text"
                value={input}
                onChange={handleInputChange}
                placeholder="Ask a question..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500"
              />
            </div>

            {/* Topic chips */}
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Quick topics:</p>
              <div className="flex flex-wrap gap-2">
                {topics.map((topic) => (
                  <button
                    key={topic.query}
                    onClick={() => handleTopicClick(topic.query)}
                    data-testid={`help-topic-${topic.query.replace(/\s+/g, '-')}`}
                    className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-primary hover:text-white dark:hover:bg-primary text-gray-700 dark:text-gray-300 rounded-full transition-colors"
                  >
                    {topic.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Answer display */}
            {answer && (
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{answer}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
