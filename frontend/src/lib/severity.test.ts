import { describe, it, expect } from 'vitest';
import { SEVERITY_COLORS } from './severity';

describe('severity.ts', () => {
  it('defines all severity levels', () => {
    expect(SEVERITY_COLORS).toHaveProperty('high');
    expect(SEVERITY_COLORS).toHaveProperty('medium');
    expect(SEVERITY_COLORS).toHaveProperty('low');
    expect(SEVERITY_COLORS).toHaveProperty('safe');
  });
  
  it('each severity has text, bg, and border colors', () => {
    Object.values(SEVERITY_COLORS).forEach((colors) => {
      expect(colors).toHaveProperty('text');
      expect(colors).toHaveProperty('bg');
      expect(colors).toHaveProperty('border');
    });
  });
  
  it('high severity uses red colors', () => {
    expect(SEVERITY_COLORS.high.text).toContain('2626');
    expect(SEVERITY_COLORS.high.bg).toContain('fef2f2');
  });
});
