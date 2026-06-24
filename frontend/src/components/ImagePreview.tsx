import { useEffect } from 'react';
import './ImagePreview.css';

interface ImagePreviewProps {
  file: File | null;
  previewUrl: string | null;
}

export function ImagePreview({ file, previewUrl }: ImagePreviewProps) {
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  if (!file || !previewUrl) return null;

  return (
    <div className="image-preview">
      <img src={previewUrl} alt={`Preview of ${file.name}`} className="image-preview-img" />
      <span className="image-preview-name">{file.name}</span>
    </div>
  );
}
