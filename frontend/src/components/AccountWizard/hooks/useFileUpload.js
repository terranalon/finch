import { useRef, useState } from 'react';

/**
 * Shared hook for file upload functionality.
 * Used by DataConnectionStep and ManualDataStep.
 *
 * @param {object} options
 * @param {string[]} options.acceptedFormats - Array of accepted file extensions (e.g., ['.csv', '.xlsx'])
 * @param {function} options.onValidationError - Callback when file validation fails
 * @returns {object} File upload state and handlers
 */
export function useFileUpload({ acceptedFormats = [], onValidationError } = {}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    if (!file) return false;

    // If no formats specified, accept all files
    if (acceptedFormats.length === 0) return true;

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    const isValid = acceptedFormats.some(
      (format) => format.toLowerCase() === ext
    );

    if (!isValid && onValidationError) {
      const formatDisplay = acceptedFormats
        .map((f) => f.replace('.', '').toUpperCase())
        .join(', ');
      onValidationError(`Invalid file format. Supported formats: ${formatDisplay}`);
    }

    return isValid;
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file && validateFile(file)) {
      setSelectedFile(file);
    }
    // Reset input to allow selecting the same file again
    if (e.target) {
      e.target.value = '';
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && validateFile(file)) {
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openFilePicker();
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
  };

  return {
    selectedFile,
    setSelectedFile,
    fileInputRef,
    handleFileSelect,
    handleFileDrop,
    handleDragOver,
    handleKeyDown,
    openFilePicker,
    clearFile,
    validateFile,
  };
}
