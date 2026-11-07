import type { Metadata } from 'next';
import './globals.css';
import './status.css';
import './interactions.css';
import './auth.css';
import AuthPanel from './auth-panel';

export const metadata: Metadata = {
  title: 'ScamShield | Threat intelligence for everyday messages',
  description: 'Explainable scam and phishing detection for links, emails, and messages.'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}<AuthPanel /></body></html>;
}
