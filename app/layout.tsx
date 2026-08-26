import type { Metadata } from 'next';
import './globals.css';
import './status.css';
import './interactions.css';

export const metadata: Metadata = {
  title: 'ScamShield | Threat intelligence for everyday messages',
  description: 'Real-time scam and phishing detection for links, emails, and messages.'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
