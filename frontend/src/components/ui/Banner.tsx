import type { ReactNode } from 'react';
import './Banner.css';

interface BannerProps {
  title?: string;
  children: ReactNode;
  variant?: 'info' | 'warning';
}

export function Banner({ title, children, variant = 'info' }: BannerProps) {
  return (
    <div className={`sybol-banner sybol-banner--${variant}`} role="status">
      {title && <p className="sybol-banner__title">{title}</p>}
      <div className="sybol-banner__body">{children}</div>
    </div>
  );
}
