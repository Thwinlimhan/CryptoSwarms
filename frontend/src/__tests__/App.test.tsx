import { test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

test('renders app title', () => {
  render(
    <App />
  );
  const elements = screen.getAllByText(/SWARM_OS/i);
  expect(elements.length).toBeGreaterThan(0);
});
