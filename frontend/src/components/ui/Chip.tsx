import type { ReactNode } from 'react';
import './Chip.css';

interface ChipProps {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
  href?: string;
}

export function Chip({ children, active, onClick, href }: ChipProps) {
  const className = `sybol-chip${active ? ' sybol-chip--active' : ''}`;
  if (href) {
    return (
      <a className={className} href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  }
  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick}>
        {children}
      </button>
    );
  }
  return <span className={className}>{children}</span>;
}
