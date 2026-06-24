import { useState, type DragEvent, type ChangeEvent } from 'react';
import './ImageUploader.css';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

interface ImageUploaderProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

export function ImageUploader({ onFileSelect, disabled }: ImageUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [typeError, setTypeError] = useState<string | null>(null);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setTypeError('Please choose a JPEG, PNG, or WebP image.');
      return;
    }
    setTypeError(null);
    onFileSelect(file);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(false);
    if (disabled) return;
    handleFiles(event.dataTransfer.files);
  };

  const onDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!disabled) setDragOver(true);
  };

  const onDragLeave = () => setDragOver(false);

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files);
    event.target.value = '';
  };

  return (
    <div>
      <div
        className={`drop-zone${dragOver ? ' drop-zone--over' : ''}${disabled ? ' drop-zone--disabled' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <p className="drop-zone-text">Drop an image here</p>
        <p className="drop-zone-hint">JPEG, PNG, or WebP</p>
        <label className="drop-zone-button">
          Choose file
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            hidden
            disabled={disabled}
            onChange={onInputChange}
          />
        </label>
      </div>
      {typeError && <p className="image-uploader-error">{typeError}</p>}
    </div>
  );
}

export function isAcceptedImageType(type: string): boolean {
  return ACCEPTED_TYPES.includes(type);
}
