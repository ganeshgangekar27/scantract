import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { PrivacyPage, TermsPage } from './LegalPage';

describe('PrivacyPage', () => {
  const renderPrivacyPage = () => {
    return render(
      <BrowserRouter>
        <PrivacyPage />
      </BrowserRouter>
    );
  };

  it('shows Privacy Policy heading', () => {
    renderPrivacyPage();
    
    expect(screen.getByText('Privacy Policy')).toBeInTheDocument();
  });

  it('contains text about deleting data but not "not legal advice"', () => {
    renderPrivacyPage();
    
    // Should contain "delete" text
    expect(screen.getByText(/delete/i)).toBeInTheDocument();
    
    // Should NOT contain "not legal advice"
    expect(screen.queryByText(/not legal advice/i)).not.toBeInTheDocument();
  });

  it('has a link back to home', () => {
    renderPrivacyPage();
    
    const homeLink = screen.getByRole('link', { name: /Back to home/i });
    expect(homeLink).toBeInTheDocument();
    expect(homeLink.getAttribute('href')).toBe('/');
  });
});

describe('TermsPage', () => {
  const renderTermsPage = () => {
    return render(
      <BrowserRouter>
        <TermsPage />
      </BrowserRouter>
    );
  };

  it('shows Terms of Service heading', () => {
    renderTermsPage();
    
    expect(screen.getByText('Terms of Service')).toBeInTheDocument();
  });

  it('contains "not legal advice" text', () => {
    renderTermsPage();
    
    expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();
  });

  it('has a link back to home', () => {
    renderTermsPage();
    
    const homeLink = screen.getByRole('link', { name: /Back to home/i });
    expect(homeLink).toBeInTheDocument();
    expect(homeLink.getAttribute('href')).toBe('/');
  });
});
