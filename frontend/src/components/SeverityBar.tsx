interface SeverityBarProps {
  high: number;
  medium: number;
  low: number;
}

export function SeverityBar({ high, medium, low }: SeverityBarProps) {
  const total = high + medium + low;

  if (total === 0) {
    return null;
  }

  const highPercent = (high / total) * 100;
  const mediumPercent = (medium / total) * 100;
  const lowPercent = (low / total) * 100;

  const segments = [];
  
  if (high > 0) {
    segments.push({
      severity: 'high',
      count: high,
      percent: highPercent,
      className: 'bg-severity-high',
    });
  }
  
  if (medium > 0) {
    segments.push({
      severity: 'medium',
      count: medium,
      percent: mediumPercent,
      className: 'bg-severity-medium',
    });
  }
  
  if (low > 0) {
    segments.push({
      severity: 'low',
      count: low,
      percent: lowPercent,
      className: 'bg-severity-low',
    });
  }

  const ariaLabel = `${high} high, ${medium} medium, ${low} low`;

  return (
    <div
      className="flex h-2 rounded-full overflow-hidden"
      data-testid="severity-bar"
      role="img"
      aria-label={ariaLabel}
    >
      {segments.map((segment) => (
        <div
          key={segment.severity}
          className={segment.className}
          style={{ width: `${segment.percent}%` }}
          title={`${segment.count} ${segment.severity}`}
        />
      ))}
    </div>
  );
}
