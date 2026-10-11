/**
 * Canned-answer help system with keyword matching.
 * No LLM, no network calls, pure function.
 */

export interface HelpAnswer {
  answer: string;
  matched: boolean;
}

const answers: Record<string, string> = {
  upload: 
    "To upload a contract, go to the Upload page from the sidebar. Click the upload area or drag and drop your file. " +
    // src: frontend/src/pages/UploadPage.tsx:260
    "Supported formats: PDF, DOCX (max 15MB). " +
    // src: frontend/src/pages/UploadPage.tsx:20-21
    "The system will process your contract and analyze it for risks.",

  filetype: 
    "We support PDF and DOCX files up to 15MB in size. " +
    // src: frontend/src/pages/UploadPage.tsx:20-21
    "Make sure your contract is in one of these formats before uploading.",

  processing: 
    "Analysis takes a few minutes because the system extracts text, segments clauses, classifies them, " +
    "performs dual RAG lookup (legal rules + reference contracts), detects risks, and generates explanations. " +
    "You'll see a 'processing' status while this happens. The owner confirms that analysis takes a few minutes.",

  risk: 
    "Risk levels are high, medium, or low. " +
    // src: frontend/src/pages/ReportView.tsx:21
    // src: frontend/tailwind.config.js:26-46
    "Each level has a distinct color: high (red), medium (yellow), low (blue). " +
    "These indicate the severity of issues found in your contract clauses.",

  clause: 
    "A clause card shows the text of a contract clause, its risk level, and a plain-language explanation. " +
    "The explanation describes why the clause was flagged and cites relevant legal rules or reference contracts. " +
    "Every flagged clause is traceable to its source text and the triggering rule.",

  contracts: 
    "To find past contracts, go to 'My Contracts' from the sidebar. " +
    // src: frontend/src/App.tsx:57
    "This page lists all contracts you've uploaded, along with their status and risk summary.",

  failed: 
    "A failed contract means the processing pipeline encountered an error. " +
    "This could be due to unsupported file format, corrupted file, or processing issues. " +
    "You can retry processing or delete the contract.",

  delete: 
    "You can delete individual contracts from the My Contracts page. " +
    "To delete all your data (contracts and account), go to Settings. " +
    // src: frontend/src/lib/api.ts:306-342
    "Deleting all data will invalidate your session and cannot be undone.",

  legal: 
    "ScanTract is NOT legal advice. We analyze contracts and flag risky or missing clauses based on " +
    "Indian legal norms, but we never say 'you should' do anything. " +
    "This system is for informational purposes only. Consult a qualified lawyer for legal advice.",
};

const keywords: Record<string, string[]> = {
  delete: ['delete my', 'delete data', 'deleting my', 'remove my data', 'erase my'],
  legal: ['legal advice', 'is this legal', 'lawyer', 'attorney'],
  upload: ['upload', 'how do i upload', 'uploading', 'submit', 'add contract'],
  filetype: ['file type', 'file format', 'what file', 'supported', 'pdf', 'docx', 'size limit'],
  processing: ['processing', 'analysis', 'why is processing', 'slow', 'how long', 'takes time'],
  risk: ['risk level', 'risk levels mean', 'severity', 'what do the risk', 'high medium low'],
  clause: ['clause card', 'what is a clause', 'clause', 'explanation'],
  contracts: ['past contract', 'my past', 'where are my', 'previous contract', 'my contracts', 'find contract'],
  failed: ['contract fail', 'failed contract', 'why did', 'broken'],
};

const fallback = 
  "I'm here to help with common questions. Try asking about: " +
  "how to upload, supported file types and size limits, why analysis takes time, " +
  "risk levels and colors, clause cards and explanations, finding past contracts, " +
  "failed contracts, deleting data, or our legal disclaimer.";

/**
 * Match user input to a canned answer using keyword matching.
 * Case-insensitive, returns fallback if no match.
 */
export function answerFor(text: string): HelpAnswer {
  const lowerText = text.toLowerCase();
  
  for (const [topic, keywordList] of Object.entries(keywords)) {
    if (keywordList.some(keyword => lowerText.includes(keyword))) {
      return {
        answer: answers[topic],
        matched: true,
      };
    }
  }
  
  return {
    answer: fallback,
    matched: false,
  };
}
