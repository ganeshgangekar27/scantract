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
});
