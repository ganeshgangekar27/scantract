import type { ClauseWithRisk } from '../types/report.types';
import { ClauseHighlight } from './ClauseHighlight';

interface ContractTextProps {
  clauses: ClauseWithRisk[];
  selectedClauseId: number | null;
  onClauseClick: (clauseId: number) => void;
}

export function ContractText({ clauses, selectedClauseId, onClauseClick }: ContractTextProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Contract Text</h2>
      <div className="space-y-1">
        {clauses.map((clause) => (
          <ClauseHighlight
            key={clause.clause_id}
            clause={clause}
            isSelected={selectedClauseId === clause.clause_id}
            onClick={() => onClauseClick(clause.clause_id)}
          />
        ))}
      </div>
    </div>
  );
}
