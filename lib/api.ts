import { analyzeInput, type Analysis, type ScanType } from './analyzer';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export type ApiState = 'connected' | 'fallback';

export type HistoryItem = {
  id: string;
  preview: string;
  type: ScanType;
  score: number;
  verdict: Analysis['verdict'];
  created_at: string;
};

export type TestCase = {
  id: string;
  title: string;
  type: ScanType;
  content: string;
  expected_verdict: Analysis['verdict'];
  tags: string[];
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal: AbortSignal.timeout(4_000) });
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  return response.json() as Promise<T>;
}

export async function analyzeWithBackend(content: string, type: ScanType): Promise<{ analysis: Analysis; state: ApiState }> {
  try {
    const response = await fetch(`${API_URL}/api/v1/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, type, save_result: true }),
      signal: AbortSignal.timeout(4_000),
    });

    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const result = await response.json();
    return {
      state: 'connected',
      analysis: {
        score: result.score,
        verdict: result.verdict,
        summary: result.summary,
        type: result.type ?? result.scan_type,
        findings: result.findings,
      },
    };
  } catch {
    return { state: 'fallback', analysis: analyzeInput(content, type) };
  }
}

export function getHistory() {
  return getJson<HistoryItem[]>('/api/v1/history?limit=20');
}

export function getTestCases() {
  return getJson<TestCase[]>('/api/v1/test-cases');
}

export function getStats() {
  return getJson<{ total_scans: number; high_risk: number; caution: number; safe: number; average_score: number }>('/api/v1/stats');
}

export async function submitReport(content: string, reason: 'missed_scam' | 'false_positive' | 'other', notes: string) {
  const response = await fetch(`${API_URL}/api/v1/reports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, reason, notes }),
    signal: AbortSignal.timeout(4_000),
  });
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  return response.json() as Promise<{ message: string }>;
}
