import { useState, useCallback } from 'react';

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  disabled?: boolean;
}

export function PromptInput({ onSubmit, disabled }: PromptInputProps) {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (prompt.trim() && !disabled) {
        onSubmit(prompt.trim());
      }
    },
    [prompt, onSubmit, disabled]
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="relative">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your candle design... (e.g., 'a sleeping cat curled up', 'art deco geometric pattern', 'oak leaf with detailed veins')"
          disabled={disabled}
          rows={3}
          className="input-field resize-none"
        />
      </div>
      <button
        type="submit"
        disabled={!prompt.trim() || disabled}
        className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none"
      >
        Generate Design
      </button>
    </form>
  );
}
