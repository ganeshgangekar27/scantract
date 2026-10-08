/**
 * Single source of truth for severity color palette
 * Used across the entire application for consistency
 */

export const SEVERITY_COLORS = {
  high: {
    text: '#dc2626',      // red-600
    bg: '#fef2f2',        // red-50
    border: '#fecaca',    // red-200
  },
  medium: {
    text: '#d97706',      // amber-600
    bg: '#fffbeb',        // amber-50
    border: '#fde68a',    // amber-200
  },
  low: {
    text: '#059669',      // emerald-600
    bg: '#f0fdf4',        // green-50
    border: '#bbf7d0',    // green-200
  },
  safe: {
    text: '#059669',      // emerald-600
    bg: '#f0fdf4',        // green-50
    border: '#bbf7d0',    // green-200
  },
} as const;

export type SeverityLevel = keyof typeof SEVERITY_COLORS;
