import type { ClauseWithRisk } from '../types/report.types';

interface ClauseHighlightProps {
  clause: ClauseWithRisk;
  isSelected: boolean;
  onClick: () => void;
}

export function ClauseHighlight({ clause, isSelected, onClick }: ClauseHighlightProps) {
  const getHighlightClasses = () => {
    if (!clause.has_risk) {
      return 'bg-white';
    }

    const baseClasses = 'border-l-4 cursor-pointer transition-colors';
    let colorClasses = '';

    switch (clause.risk_severity) {
      case 'high':
        colorClasses = 'bg-red-50 hover:bg-red-100 border-red-500';
        break;
      case 'medium':
        colorClasses = 'bg-yellow-50 hover:bg-yellow-100 border-yellow-500';
        break;
      case 'low':
        colorClasses = 'bg-blue-50 hover:bg-blue-100 border-blue-500';
        break;
      default:
        colorClasses = 'bg-white';
    }

    return `${baseClasses} ${colorClasses}`;
  };

  const selectedClasses = isSelected ? 'ring-2 ring-blue-500' : '';
  const cursorClasses = clause.has_risk ? 'cursor-pointer' : '';

  return (
    <div
      onClick={clause.has_risk ? onClick : undefined}
      className={`p-4 mb-2 rounded-md ${getHighlightClasses()} ${selectedClasses} ${cursorClasses}`}
    >
      <div className="flex items-start">
        <span className="font-semibold text-gray-700 mr-2 flex-shrink-0">
          {clause.clause_number}
        </span>
        <p className="text-gray-900">{clause.clause_text}</p>
      </div>
    </div>
  );
}
