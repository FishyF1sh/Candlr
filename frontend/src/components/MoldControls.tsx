import { useState, useCallback, useEffect } from 'react';
import type { MoldSettings } from '../types';
import { DEFAULT_MOLD_SETTINGS } from '../types';

interface MoldControlsProps {
  onSettingsChange: (settings: MoldSettings) => void;
  disabled?: boolean;
}

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (value: number) => void;
  disabled?: boolean;
}

function Slider({ label, value, min, max, step, unit, onChange, disabled }: SliderProps) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium text-charcoal">{label}</label>
        <span className="text-sm text-warm-gray">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        disabled={disabled}
        className="w-full h-2 bg-warm-gray/20 rounded-full appearance-none cursor-pointer
                   [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5
                   [&::-webkit-slider-thumb]:bg-terracotta [&::-webkit-slider-thumb]:rounded-full
                   [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer
                   [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-110
                   disabled:opacity-50 disabled:cursor-not-allowed"
      />
    </div>
  );
}

export function MoldControls({ onSettingsChange, disabled }: MoldControlsProps) {
  const [settings, setSettings] = useState<MoldSettings>(DEFAULT_MOLD_SETTINGS);
  const [hasChanges, setHasChanges] = useState(false);

  const updateSetting = useCallback(<K extends keyof MoldSettings>(key: K, value: MoldSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  }, []);

  const applyChanges = useCallback(() => {
    onSettingsChange(settings);
    setHasChanges(false);
  }, [settings, onSettingsChange]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (hasChanges) {
        applyChanges();
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [settings, hasChanges, applyChanges]);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-charcoal mb-4" style={{ fontFamily: 'var(--font-serif)' }}>
          Mold Settings
        </h3>

        <div className="space-y-5">
          <Slider
            label="Wall Thickness"
            value={settings.wallThickness}
            min={2}
            max={20}
            step={0.5}
            unit="mm"
            onChange={(v) => updateSetting('wallThickness', v)}
            disabled={disabled}
          />

          <Slider
            label="Maximum Width"
            value={settings.maxWidth}
            min={20}
            max={300}
            step={5}
            unit="mm"
            onChange={(v) => updateSetting('maxWidth', v)}
            disabled={disabled}
          />

          <Slider
            label="Maximum Height"
            value={settings.maxHeight}
            min={20}
            max={300}
            step={5}
            unit="mm"
            onChange={(v) => updateSetting('maxHeight', v)}
            disabled={disabled}
          />

          <Slider
            label="Relief Depth"
            value={settings.maxDepth}
            min={10}
            max={100}
            step={5}
            unit="mm"
            onChange={(v) => updateSetting('maxDepth', v)}
            disabled={disabled}
          />
        </div>
      </div>

    </div>
  );
}
