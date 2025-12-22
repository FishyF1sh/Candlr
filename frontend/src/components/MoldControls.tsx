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

interface ToggleProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

function Toggle({ label, description, checked, onChange, disabled }: ToggleProps) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <div className="relative mt-0.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only peer"
        />
        <div
          className="w-10 h-6 bg-warm-gray/30 rounded-full
                      peer-checked:bg-terracotta peer-disabled:opacity-50
                      transition-colors duration-200"
        />
        <div
          className="absolute left-1 top-1 w-4 h-4 bg-cream rounded-full shadow
                      peer-checked:translate-x-4 peer-disabled:opacity-50
                      transition-transform duration-200"
        />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-charcoal group-hover:text-terracotta transition-colors">
          {label}
        </p>
        <p className="text-xs text-warm-gray">{description}</p>
      </div>
    </label>
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

      <div className="border-t border-warm-gray/20 pt-5">
        <h4 className="text-md font-medium text-charcoal mb-4">Wick Hole</h4>

        <div className="space-y-4">
          <Toggle
            label="Include Wick Hole"
            description="Add a hole for the candle wick"
            checked={settings.wickEnabled}
            onChange={(v) => updateSetting('wickEnabled', v)}
            disabled={disabled}
          />

          {settings.wickEnabled && (
            <div className="space-y-4 pl-2 border-l-2 border-terracotta/20">
              <Slider
                label="Wick Diameter"
                value={settings.wickDiameter}
                min={1}
                max={10}
                step={0.5}
                unit="mm"
                onChange={(v) => updateSetting('wickDiameter', v)}
                disabled={disabled}
              />

              <Slider
                label="Wick Length"
                value={settings.wickLength}
                min={5}
                max={200}
                step={5}
                unit="mm"
                onChange={(v) => updateSetting('wickLength', v)}
                disabled={disabled}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
