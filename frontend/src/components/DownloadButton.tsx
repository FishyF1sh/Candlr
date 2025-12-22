import { useCallback } from 'react';

interface DownloadButtonProps {
  stlBlob: Blob | null;
  disabled?: boolean;
}

export function DownloadButton({ stlBlob, disabled }: DownloadButtonProps) {
  const handleDownload = useCallback(() => {
    if (!stlBlob) return;

    const url = URL.createObjectURL(stlBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `candle_mold_${Date.now()}.stl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [stlBlob]);

  return (
    <button
      onClick={handleDownload}
      disabled={!stlBlob || disabled}
      className="btn-primary w-full flex items-center justify-center gap-2
                 disabled:opacity-50 disabled:cursor-not-allowed
                 disabled:hover:translate-y-0 disabled:hover:shadow-none"
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
        />
      </svg>
      Download STL
    </button>
  );
}
