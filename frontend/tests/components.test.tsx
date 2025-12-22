import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ImageUpload } from '../src/components/ImageUpload';
import { PromptInput } from '../src/components/PromptInput';
import { DownloadButton } from '../src/components/DownloadButton';
import { MoldControls } from '../src/components/MoldControls';
import { ProcessingIndicator } from '../src/components/ProcessingIndicator';

describe('ImageUpload', () => {
  it('renders upload area with instructions', () => {
    const onImageSelect = vi.fn();
    render(<ImageUpload onImageSelect={onImageSelect} />);

    expect(screen.getByText(/drop your image here/i)).toBeInTheDocument();
    expect(screen.getByText(/or click to browse/i)).toBeInTheDocument();
  });

  it('has a hidden file input', () => {
    const onImageSelect = vi.fn();
    render(<ImageUpload onImageSelect={onImageSelect} />);

    const input = document.querySelector('input[type="file"]');
    expect(input).toBeInTheDocument();
    expect(input).toHaveClass('hidden');
  });

  it('accepts image files only', () => {
    const onImageSelect = vi.fn();
    render(<ImageUpload onImageSelect={onImageSelect} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input?.accept).toBe('image/*');
  });

  it('is disabled when disabled prop is true', () => {
    const onImageSelect = vi.fn();
    render(<ImageUpload onImageSelect={onImageSelect} disabled />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input?.disabled).toBe(true);
  });
});

describe('PromptInput', () => {
  it('renders textarea and submit button', () => {
    const onSubmit = vi.fn();
    render(<PromptInput onSubmit={onSubmit} />);

    expect(screen.getByPlaceholderText(/describe your candle design/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate design/i })).toBeInTheDocument();
  });

  it('button is disabled when input is empty', () => {
    const onSubmit = vi.fn();
    render(<PromptInput onSubmit={onSubmit} />);

    const button = screen.getByRole('button', { name: /generate design/i });
    expect(button).toBeDisabled();
  });

  it('button is enabled when input has text', () => {
    const onSubmit = vi.fn();
    render(<PromptInput onSubmit={onSubmit} />);

    const textarea = screen.getByPlaceholderText(/describe your candle design/i);
    fireEvent.change(textarea, { target: { value: 'a cat' } });

    const button = screen.getByRole('button', { name: /generate design/i });
    expect(button).not.toBeDisabled();
  });

  it('calls onSubmit with prompt when form is submitted', () => {
    const onSubmit = vi.fn();
    render(<PromptInput onSubmit={onSubmit} />);

    const textarea = screen.getByPlaceholderText(/describe your candle design/i);
    fireEvent.change(textarea, { target: { value: 'a sleeping cat' } });

    const button = screen.getByRole('button', { name: /generate design/i });
    fireEvent.click(button);

    expect(onSubmit).toHaveBeenCalledWith('a sleeping cat');
  });
});

describe('DownloadButton', () => {
  it('renders download button', () => {
    render(<DownloadButton stlBlob={null} />);

    expect(screen.getByRole('button', { name: /download stl/i })).toBeInTheDocument();
  });

  it('is disabled when stlBlob is null', () => {
    render(<DownloadButton stlBlob={null} />);

    const button = screen.getByRole('button', { name: /download stl/i });
    expect(button).toBeDisabled();
  });

  it('is enabled when stlBlob is provided', () => {
    const blob = new Blob(['test'], { type: 'application/octet-stream' });
    render(<DownloadButton stlBlob={blob} />);

    const button = screen.getByRole('button', { name: /download stl/i });
    expect(button).not.toBeDisabled();
  });
});

describe('MoldControls', () => {
  it('renders all control sliders', () => {
    const onSettingsChange = vi.fn();
    render(<MoldControls onSettingsChange={onSettingsChange} />);

    expect(screen.getByText(/wall thickness/i)).toBeInTheDocument();
    expect(screen.getByText(/maximum width/i)).toBeInTheDocument();
    expect(screen.getByText(/maximum height/i)).toBeInTheDocument();
    expect(screen.getByText(/relief depth/i)).toBeInTheDocument();
  });
});

describe('ProcessingIndicator', () => {
  it('renders with the provided step message', () => {
    render(<ProcessingIndicator step="Extracting subject..." />);

    expect(screen.getByText(/creating your mold/i)).toBeInTheDocument();
    expect(screen.getByText(/extracting subject/i)).toBeInTheDocument();
  });
});
