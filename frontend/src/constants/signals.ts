export const SIGNAL_LABELS = {
  m: { label: 'Metadata', description: 'EXIF / file metadata signals' },
  a: { label: 'Artifacts', description: 'Compression & editing artifacts' },
  v: { label: 'Visual', description: 'Deepfake / visual authenticity model' },
  p: { label: 'Provenance', description: 'Perceptual hash & provenance' },
} as const;

export type SignalKey = keyof typeof SIGNAL_LABELS;

export const SIGNAL_KEYS: SignalKey[] = ['m', 'a', 'v', 'p'];
