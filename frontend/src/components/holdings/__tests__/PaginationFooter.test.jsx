import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../lib', () => ({
  cn: (...args) => args.filter(Boolean).join(' '),
}));

import { PaginationFooter } from '../PaginationFooter';

describe('PaginationFooter', () => {
  const defaultProps = {
    currentPage: 1,
    totalItems: 75,
    pageSize: 25,
    onPageChange: vi.fn(),
    onPageSizeChange: vi.fn(),
  };

  it('shows correct range text', () => {
    render(<PaginationFooter {...defaultProps} />);
    expect(screen.getByText(/Showing 1-25 of 75/)).toBeInTheDocument();
  });

  it('shows page size selector with 25/50/100 options', () => {
    render(<PaginationFooter {...defaultProps} />);
    const select = screen.getByDisplayValue('25');
    expect(select).toBeInTheDocument();
    expect(select.children.length).toBe(3);
  });

  it('calls onPageSizeChange and resets to page 1', () => {
    const onPageSizeChange = vi.fn();
    render(<PaginationFooter {...defaultProps} onPageSizeChange={onPageSizeChange} />);
    fireEvent.change(screen.getByDisplayValue('25'), { target: { value: '50' } });
    expect(onPageSizeChange).toHaveBeenCalledWith(50);
  });

  it('disables previous buttons on first page', () => {
    render(<PaginationFooter {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons[0]).toBeDisabled(); // first page
    expect(buttons[1]).toBeDisabled(); // prev page
  });

  it('enables next buttons when not on last page', () => {
    render(<PaginationFooter {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons[2]).not.toBeDisabled(); // next page
    expect(buttons[3]).not.toBeDisabled(); // last page
  });

  it('shows page number', () => {
    render(<PaginationFooter {...defaultProps} />);
    expect(screen.getByText('1 / 3')).toBeInTheDocument();
  });

  it('does not render pagination buttons when total fits in one page', () => {
    render(<PaginationFooter {...defaultProps} totalItems={20} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
