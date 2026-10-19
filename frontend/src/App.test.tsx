// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from './App';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('AgentOS workspace', () => {
  it('shows honest offline status when the API is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    render(<App/>);
    expect(await screen.findByText('API offline')).toBeTruthy();
    expect(screen.getByText('Nothing running right now')).toBeTruthy();
  });

  it('opens the agent composer from the dashboard', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    render(<App/>);
    fireEvent.click(screen.getByRole('button', {name:/New workflow/i}));
    expect(screen.getByText('What should your agent do?')).toBeTruthy();
    expect(screen.getByText('You stay in control')).toBeTruthy();
  });
});
