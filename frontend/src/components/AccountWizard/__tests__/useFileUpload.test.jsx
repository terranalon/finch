import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFileUpload } from '../hooks/useFileUpload';

describe('useFileUpload', () => {
  it('initializes with null selected file', () => {
    const { result } = renderHook(() => useFileUpload());
    expect(result.current.selectedFile).toBeNull();
  });

  it('accepts valid file format', () => {
    const { result } = renderHook(() =>
      useFileUpload({ acceptedFormats: ['.csv', '.xlsx'] })
    );

    const file = new File(['content'], 'test.csv', { type: 'text/csv' });
    const event = { target: { files: [file], value: '' } };

    act(() => {
      result.current.handleFileSelect(event);
    });

    expect(result.current.selectedFile).toBe(file);
  });

  it('rejects invalid file format', () => {
    const onValidationError = vi.fn();
    const { result } = renderHook(() =>
      useFileUpload({
        acceptedFormats: ['.csv'],
        onValidationError,
      })
    );

    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const event = { target: { files: [file], value: '' } };

    act(() => {
      result.current.handleFileSelect(event);
    });

    expect(result.current.selectedFile).toBeNull();
    expect(onValidationError).toHaveBeenCalledWith(
      'Invalid file format. Supported formats: CSV'
    );
  });

  it('accepts any file when no formats specified', () => {
    const { result } = renderHook(() => useFileUpload());

    const file = new File(['content'], 'test.anything', { type: 'application/octet-stream' });
    const event = { target: { files: [file], value: '' } };

    act(() => {
      result.current.handleFileSelect(event);
    });

    expect(result.current.selectedFile).toBe(file);
  });

  it('handles file drop', () => {
    const { result } = renderHook(() =>
      useFileUpload({ acceptedFormats: ['.csv'] })
    );

    const file = new File(['content'], 'test.csv', { type: 'text/csv' });
    const event = {
      preventDefault: vi.fn(),
      dataTransfer: { files: [file] },
    };

    act(() => {
      result.current.handleFileDrop(event);
    });

    expect(event.preventDefault).toHaveBeenCalled();
    expect(result.current.selectedFile).toBe(file);
  });

  it('clears file selection', () => {
    const { result } = renderHook(() => useFileUpload());

    const file = new File(['content'], 'test.csv', { type: 'text/csv' });
    const event = { target: { files: [file], value: '' } };

    act(() => {
      result.current.handleFileSelect(event);
    });

    expect(result.current.selectedFile).toBe(file);

    act(() => {
      result.current.clearFile();
    });

    expect(result.current.selectedFile).toBeNull();
  });

  it('handles keyboard navigation', () => {
    const { result } = renderHook(() => useFileUpload());

    // Mock fileInputRef click
    const mockClick = vi.fn();
    result.current.fileInputRef.current = { click: mockClick };

    const enterEvent = { key: 'Enter', preventDefault: vi.fn() };
    const spaceEvent = { key: ' ', preventDefault: vi.fn() };
    const otherEvent = { key: 'a', preventDefault: vi.fn() };

    act(() => {
      result.current.handleKeyDown(enterEvent);
    });
    expect(mockClick).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.handleKeyDown(spaceEvent);
    });
    expect(mockClick).toHaveBeenCalledTimes(2);

    act(() => {
      result.current.handleKeyDown(otherEvent);
    });
    expect(mockClick).toHaveBeenCalledTimes(2); // Not called for 'a' key
  });

  it('validates file correctly', () => {
    const { result } = renderHook(() =>
      useFileUpload({ acceptedFormats: ['.csv', '.xlsx'] })
    );

    const validFile = new File(['content'], 'test.csv', { type: 'text/csv' });
    const invalidFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });

    expect(result.current.validateFile(validFile)).toBe(true);
    expect(result.current.validateFile(invalidFile)).toBe(false);
    expect(result.current.validateFile(null)).toBe(false);
  });

  it('handles case-insensitive extension matching', () => {
    const { result } = renderHook(() =>
      useFileUpload({ acceptedFormats: ['.CSV'] })
    );

    const file = new File(['content'], 'test.csv', { type: 'text/csv' });
    expect(result.current.validateFile(file)).toBe(true);

    const upperFile = new File(['content'], 'test.CSV', { type: 'text/csv' });
    expect(result.current.validateFile(upperFile)).toBe(true);
  });
});
