import type { HTMLAttributes, ReactNode } from 'react';
import './Card.css';

type CardVariant = 'default' | 'accent' | 'vc';

interface CardProps extends HTMLAttributes<HTMLElement> {
  variant?: CardVariant;
  children: ReactNode;
  as?: 'section' | 'article' | 'div';
}

export function Card({
  variant = 'default',
  className = '',
  children,
  as: Tag = 'section',
  ...props
}: CardProps) {
  return (
    <Tag
      className={`sybol-card sybol-card--${variant} ${className}`.trim()}
      {...props}
    >
      {children}
    </Tag>
  );
}
