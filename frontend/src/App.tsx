import { useState } from 'react';
import { ImageUpload } from './components/ImageUpload';
import { PromptInput } from './components/PromptInput';
import { MoldPreview } from './components/MoldPreview';
import { MoldControls } from './components/MoldControls';
import { DownloadButton } from './components/DownloadButton';
import { ProcessingIndicator } from './components/ProcessingIndicator';
import { useGeneration } from './hooks/useGeneration';

type InputMode = 'image' | 'prompt';

function App() {
  const [inputMode, setInputMode] = useState<InputMode>('image');
  const { state, processImage, processPrompt, regenerateMold, reset } = useGeneration();

  const handleImageSelect = (base64: string) => {
    processImage(base64);
  };

  const handlePromptSubmit = (prompt: string) => {
    processPrompt(prompt);
  };

  return (
    <div className="min-h-screen">
      <header className="py-8 px-6">
        <div className="max-w-5xl mx-auto">
          <h1
            className="text-4xl md:text-5xl font-bold text-charcoal tracking-tight"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            Candlr
          </h1>
          <p className="mt-2 text-warm-gray text-lg">
            Transform images into custom candle molds
          </p>
        </div>
      </header>

      <main className="px-6 pb-16">
        <div className="max-w-5xl mx-auto">
          {state.step === 'input' && (
            <div className="max-w-xl mx-auto">
              <div className="flex gap-2 mb-6">
                <button
                  onClick={() => setInputMode('image')}
                  className={`flex-1 py-2 px-4 rounded-sm text-sm font-medium transition-all duration-200 ${
                    inputMode === 'image'
                      ? 'bg-charcoal text-cream'
                      : 'bg-cream-dark text-charcoal hover:bg-charcoal/10'
                  }`}
                >
                  Upload Image
                </button>
                <button
                  onClick={() => setInputMode('prompt')}
                  className={`flex-1 py-2 px-4 rounded-sm text-sm font-medium transition-all duration-200 ${
                    inputMode === 'prompt'
                      ? 'bg-charcoal text-cream'
                      : 'bg-cream-dark text-charcoal hover:bg-charcoal/10'
                  }`}
                >
                  Describe It
                </button>
              </div>

              <div className="card">
                {inputMode === 'image' ? (
                  <ImageUpload onImageSelect={handleImageSelect} />
                ) : (
                  <PromptInput onSubmit={handlePromptSubmit} />
                )}
              </div>

              <p className="mt-6 text-center text-sm text-warm-gray">
                Your image will be processed to create a 3D-printable mold for silicone casting.
              </p>
            </div>
          )}

          {state.step === 'processing' && (
            <div className="max-w-xl mx-auto card">
              <ProcessingIndicator
                step={state.currentProcessingStep || 'Processing...'}
                promptInfo={state.currentPromptInfo}
              />
            </div>
          )}

          {state.step === 'customize' && (
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-6">
                <MoldPreview stlBlob={state.stlBlob} />
                <DownloadButton stlBlob={state.stlBlob} />
              </div>

              <div className="card">
                <MoldControls onSettingsChange={regenerateMold} />

                <div className="mt-8 pt-6 border-t border-warm-gray/20">
                  <button onClick={reset} className="btn-secondary w-full">
                    Start Over
                  </button>
                </div>
              </div>
            </div>
          )}

          {state.step === 'error' && (
            <div className="max-w-xl mx-auto">
              <div className="card text-center">
                <div className="w-16 h-16 mx-auto mb-4 text-terracotta">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                    />
                  </svg>
                </div>
                <h2
                  className="text-xl font-semibold text-charcoal mb-2"
                  style={{ fontFamily: 'var(--font-serif)' }}
                >
                  Something went wrong
                </h2>
                <p className="text-warm-gray mb-6">{state.errorMessage}</p>
                <button onClick={reset} className="btn-primary">
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      <footer className="py-6 px-6 border-t border-warm-gray/10">
        <div className="max-w-5xl mx-auto text-center text-sm text-warm-gray">
          <p>No data is collected or stored. Your images are processed and forgotten.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
