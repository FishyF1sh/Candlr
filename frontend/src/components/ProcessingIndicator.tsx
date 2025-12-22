import { useState } from 'react';
import type { PromptInfo } from '../types';

interface ProcessingIndicatorProps {
  step: string;
  promptInfo?: PromptInfo | null;
}

export function ProcessingIndicator({ step, promptInfo }: ProcessingIndicatorProps) {
  const [isPromptExpanded, setIsPromptExpanded] = useState(false);

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative w-20 h-20 mb-6">
        <div className="absolute inset-0 border-4 border-cream-dark rounded-full" />
        <div className="absolute inset-0 border-4 border-terracotta border-t-transparent rounded-full animate-spin" />
        <div className="absolute inset-2 border-4 border-sage/30 border-b-transparent rounded-full animate-spin-slow" />
      </div>

      <p className="text-lg font-medium text-charcoal mb-2" style={{ fontFamily: 'var(--font-serif)' }}>
        Creating your mold
      </p>
      <p className="text-sm text-warm-gray animate-pulse mb-4">{step}</p>

      {promptInfo && (
        <div className="w-full max-w-2xl mt-4">
          <button
            onClick={() => setIsPromptExpanded(!isPromptExpanded)}
            className="flex items-center gap-2 mx-auto text-sm text-sage hover:text-sage-dark transition-colors"
          >
            <span className="font-medium">View AI Prompt</span>
            <svg
              className={`w-4 h-4 transition-transform ${isPromptExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {isPromptExpanded && (
            <div className="mt-4 p-4 bg-cream-dark/50 rounded-lg border border-cream-dark">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-terracotta uppercase tracking-wide">
                  Model: {promptInfo.modelUsed}
                </span>
              </div>
              <pre className="text-xs text-charcoal/80 whitespace-pre-wrap font-mono leading-relaxed max-h-48 overflow-y-auto">
                {promptInfo.promptUsed}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
