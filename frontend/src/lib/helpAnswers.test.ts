import { describe, it, expect } from 'vitest';
import { answerFor } from './helpAnswers';

describe('helpAnswers', () => {
  it('matches upload topic and includes relevant info', () => {
    const result = answerFor('how do I upload a contract?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('Upload page');
    expect(result.answer).toContain('PDF, DOCX');
  });

  it('matches file type topic with case insensitive matching', () => {
    const result = answerFor('WHAT FILE TYPES are supported?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('PDF');
    expect(result.answer).toContain('15MB');
  });

  it('matches processing topic and mentions time', () => {
    const result = answerFor('why is processing so slow?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('few minutes');
    expect(result.answer).toContain('processing');
  });

  it('matches risk topic and mentions levels', () => {
    const result = answerFor('what do the risk levels mean?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('high');
    expect(result.answer).toContain('medium');
    expect(result.answer).toContain('low');
    expect(result.answer).toContain('safe');
  });

  it('matches clause topic and mentions explanation', () => {
    const result = answerFor('what is a clause card?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('clause');
    expect(result.answer).toContain('explanation');
  });

  it('matches contracts topic and mentions sidebar', () => {
    const result = answerFor('where are my past contracts?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('My Contracts');
    expect(result.answer).toContain('sidebar');
  });

  it('matches failed topic and mentions error', () => {
    const result = answerFor('why did my contract fail?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('failed');
    expect(result.answer).toContain('error');
  });

  it('matches delete topic and mentions data', () => {
    const result = answerFor('how do I delete my data?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('delete');
    expect(result.answer).toContain('Settings');
  });

  it('matches legal disclaimer topic', () => {
    const result = answerFor('is this legal advice?');
    expect(result.matched).toBe(true);
    expect(result.answer).toContain('NOT legal advice');
    expect(result.answer).toContain('lawyer');
  });

  it('returns fallback for unmatched input', () => {
    const result = answerFor('xyz gibberish 123 qwerty');
    expect(result.matched).toBe(false);
    expect(result.answer).toContain('common questions');
    expect(result.answer).toContain('upload');
  });

  it('returns fallback for empty input', () => {
    const result = answerFor('');
    expect(result.matched).toBe(false);
    expect(result.answer).toContain('common questions');
  });

  // Table-driven tests with exact topic assertions
  describe('realistic user phrasings', () => {
    const testCases: Array<{ input: string; expectedTopic: string | null; description: string }> = [
      { input: 'how do I delete my data', expectedTopic: 'delete', description: 'delete data question' },
      { input: 'do I need an account', expectedTopic: null, description: 'account question (no match)' },
      { input: 'what file types are supported', expectedTopic: 'filetype', description: 'file types question' },
      { input: 'is docx ok?', expectedTopic: 'filetype', description: 'docx format check' },
      { input: 'what does high risk mean?', expectedTopic: 'risk', description: 'risk level meaning' },
      { input: 'how long does it take', expectedTopic: 'processing', description: 'processing time' },
      { input: 'my contract failed', expectedTopic: 'failed', description: 'failed contract' },
      { input: 'where are my old contracts', expectedTopic: 'contracts', description: 'finding old contracts' },
      { input: 'is this legal advice', expectedTopic: 'legal', description: 'legal advice disclaimer' },
      { input: 'can I upload a pdf', expectedTopic: 'upload', description: 'upload question' },
      { input: 'what is a clause', expectedTopic: 'clause', description: 'clause explanation' },
      { input: 'why is analysis slow', expectedTopic: 'processing', description: 'analysis speed' },
      { input: 'delete my account', expectedTopic: 'delete', description: 'account deletion' },
      { input: 'how to submit contract', expectedTopic: 'upload', description: 'submit contract' },
      { input: 'pdf supported?', expectedTopic: 'filetype', description: 'pdf support check' },
      { input: 'uploaded successfully', expectedTopic: null, description: 'uploaded should not match upload (word boundary)' },
      { input: 'random nonsense text', expectedTopic: null, description: 'gibberish input 1' },
      { input: 'xyzabc 123456', expectedTopic: null, description: 'gibberish input 2' },
    ];

    testCases.forEach(({ input, expectedTopic, description }) => {
      it(`${description}: "${input}"`, () => {
        const result = answerFor(input);
        expect(result.topic).toBe(expectedTopic);
        if (expectedTopic === null) {
          expect(result.matched).toBe(false);
        } else {
          expect(result.matched).toBe(true);
        }
      });
    });
  });
});
