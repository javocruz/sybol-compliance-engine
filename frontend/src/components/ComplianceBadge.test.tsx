import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ComplianceBadge } from '../components/ComplianceBadge';

describe('ComplianceBadge', () => {
  it('renders compliant label', () => {
    render(<ComplianceBadge status="compliant" />);
    expect(screen.getByText(/compliant/i)).toBeTruthy();
  });
});
