export type ScanType = 'URL' | 'Email' | 'Message';

export type Finding = {
  label: string;
  detail: string;
  severity: 'high' | 'medium' | 'low';
  recommendation?: string;
};

export type Analysis = {
  score: number;
  verdict: 'Safe' | 'Caution' | 'High risk';
  summary: string;
  findings: Finding[];
  type: ScanType;
};

const rules: Array<{ pattern: RegExp; label: string; detail: string; severity: Finding['severity']; points: number }> = [
  { pattern: /urgent|immediately|within \d+ hours?|act now|last warning/i, label: 'Urgency language', detail: 'Pushes you to act before you can verify the request.', severity: 'high', points: 24 },
  { pattern: /password|passcode|one[- ]time|otp|verification code|login/i, label: 'Credential request', detail: 'Legitimate teams rarely ask for secrets over chat or email.', severity: 'high', points: 28 },
  { pattern: /gift card|crypto|bitcoin|wire transfer|send money|payment/i, label: 'Unusual payment request', detail: 'Payment methods are difficult to reverse and commonly used by scammers.', severity: 'high', points: 25 },
  { pattern: /free|winner|won|reward|prize|claim/i, label: 'Too-good-to-be-true offer', detail: 'Unexpected rewards are a common lure for harvesting information.', severity: 'medium', points: 14 },
  { pattern: /bit\.ly|tinyurl|t\.co|goo\.gl|shorturl/i, label: 'Shortened link', detail: 'The final destination is hidden until the link is opened.', severity: 'medium', points: 18 },
  { pattern: /verify|suspend|locked|unusual activity|security alert/i, label: 'Fear-based framing', detail: 'Threats about account access create pressure and bypass skepticism.', severity: 'medium', points: 16 },
  { pattern: /@.*\.(ru|cn|top|xyz|click)\b/i, label: 'Suspicious sender domain', detail: 'The sender domain has signals associated with disposable infrastructure.', severity: 'high', points: 22 },
];

export function analyzeInput(input: string, type: ScanType): Analysis {
  const findings = rules.filter((rule) => rule.pattern.test(input)).map(({ label, detail, severity }) => ({ label, detail, severity }));
  const hasUrl = /https?:\/\/|www\./i.test(input);
  const score = Math.min(99, Math.max(6, findings.reduce((total, _, index) => total + (rules.find((rule) => rule.label === findings[index].label)?.points ?? 0), hasUrl ? 8 : 4)));
  const verdict = score >= 65 ? 'High risk' : score >= 30 ? 'Caution' : 'Safe';
  const summary = verdict === 'High risk'
    ? 'This looks designed to create urgency and get something valuable from you.'
    : verdict === 'Caution'
      ? 'A few patterns deserve a closer look before you reply or click.'
      : 'No strong scam patterns detected. Still verify unexpected requests independently.';

  return { score, verdict, summary, findings, type };
}
