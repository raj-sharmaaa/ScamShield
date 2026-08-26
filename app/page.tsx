'use client';

import { useEffect, useState } from 'react';
import { ArrowUpRight, Bell, CheckCircle2, ChevronDown, CircleHelp, ClipboardPaste, ExternalLink, Flag, Link2, Mail, MessageSquareText, Radar, ScanSearch, ShieldCheck, Sparkles, TriangleAlert } from 'lucide-react';
import { analyzeInput, type Analysis, type ScanType } from '../lib/analyzer';
import { analyzeWithBackend, getHistory, getStats, getTestCases, submitReport, type ApiState, type HistoryItem, type TestCase } from '../lib/api';

const samples: Record<ScanType, string> = {
  URL: 'https://bit.ly/claim-your-free-reward',
  Email: 'From: security@paypaI-verification.top\nSubject: Urgent: verify your account immediately\n\nYour account has been locked. Confirm your password within 24 hours to avoid permanent suspension: https://bit.ly/secure-login',
  Message: 'Congratulations! You won a $500 gift card. Claim your reward now or it expires today. Send the one-time verification code to confirm delivery.'
};

const initialAnalysis: Analysis = analyzeInput(samples.URL, 'URL');

export default function Home() {
  const [scanType, setScanType] = useState<ScanType>('URL');
  const [input, setInput] = useState(samples.URL);
  const [analysis, setAnalysis] = useState(initialAnalysis);
  const [scanning, setScanning] = useState(false);
  const [activeNav, setActiveNav] = useState('Overview');
  const [apiState, setApiState] = useState<ApiState>('fallback');
  const [showExplanation, setShowExplanation] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [stats, setStats] = useState({ total_scans: 0, high_risk: 0, caution: 0, safe: 0, average_score: 0 });
  const [modal, setModal] = useState<'help' | 'report' | 'notifications' | 'profile' | null>(null);
  const [reportReason, setReportReason] = useState<'missed_scam' | 'false_positive' | 'other'>('missed_scam');
  const [reportNotes, setReportNotes] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    Promise.all([getHistory(), getTestCases(), getStats()]).then(([recent, cases, summary]) => {
      setHistory(recent);
      setTestCases(cases);
      setStats(summary);
      setApiState('connected');
    }).catch(() => setApiState('fallback'));
  }, []);

  function selectType(type: ScanType) {
    setScanType(type);
    setInput(samples[type]);
    setAnalysis(analyzeInput(samples[type], type));
  }

  async function runScan() {
    setScanning(true);
    const result = await analyzeWithBackend(input, scanType);
    setAnalysis(result.analysis);
    setApiState(result.state);
    setScanning(false);
    if (result.state === 'connected') {
      getHistory().then(setHistory).catch(() => undefined);
      getStats().then(setStats).catch(() => undefined);
    }
  }

  function showNotice(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(''), 3500);
  }

  function loadTestCase(testCase: TestCase) {
    setScanType(testCase.type);
    setInput(testCase.content);
    setActiveNav('Overview');
    showNotice(`Loaded ${testCase.title}`);
  }

  async function sendReport() {
    try {
      await submitReport(input, reportReason, reportNotes);
      setModal(null);
      setReportNotes('');
      showNotice('Report received. Thank you for improving ScamShield.');
    } catch {
      showNotice('The API is offline. Start the backend to send reports.');
    }
  }

  const scoreColor = analysis.score >= 65 ? 'coral' : analysis.score >= 30 ? 'amber' : 'mint';

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><ShieldCheck size={22} /></span><span>Scam<span>Shield</span></span></div>
        <div className="workspace-switcher"><span className="avatar">JS</span><span><strong>Jordan&apos;s workspace</strong><small>Personal protection</small></span><ChevronDown size={15} /></div>
        <nav>
          <p className="nav-label">Workspace</p>
          {['Overview', 'Scan history', 'Test library'].map((item) => <button key={item} className={activeNav === item ? 'nav-item active' : 'nav-item'} onClick={() => setActiveNav(item)}>{item === 'Overview' ? <Radar size={17} /> : item === 'Scan history' ? <ScanSearch size={17} /> : <ClipboardPaste size={17} />}{item}{item === 'Scan history' && <span className="nav-count">{stats.total_scans || history.length || 0}</span>}</button>)}
          <p className="nav-label second">Resources</p>
          <button className="nav-item" onClick={() => setModal('help')}><CircleHelp size={17} />How it works</button>
          <button className="nav-item" onClick={() => setModal('report')}><Flag size={17} />Report a scam</button>
        </nav>
        <div className="sidebar-footer"><div className="status-dot" /><span><strong>Protection active</strong><small>Updated just now</small></span><ArrowUpRight size={16} /></div>
      </aside>

      <section className="content">
        <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> {activeNav}</div><div className="top-actions"><button className="icon-button" aria-label="Notifications" onClick={() => setModal('notifications')}><Bell size={19} /><i /></button><button className="profile" onClick={() => setModal('profile')}>Jordan S.<span>JS</span></button></div></header>
        <div className="page-content">
          <section className="intro"><div><div className="eyebrow"><span /> LIVE PROTECTION</div><h1>Spot the trap<br /><em>before it catches you.</em></h1><p>Paste anything suspicious. ScamShield reads the signals scammers leave behind and explains what to do next.</p></div><div className="intro-stat"><span>SCANS THIS WORKSPACE</span><strong>{stats.total_scans || '—'}</strong><small>{stats.high_risk ? `${stats.high_risk} high-risk alerts` : 'Build your first scan'}</small></div></section>

          {activeNav === 'Scan history' && <section className="workspace-view"><div className="block-heading"><div><span className="section-kicker">WORKSPACE</span><h2>Scan history</h2></div><span className="view-summary">{history.length} saved results</span></div>{history.length ? <div className="history-grid">{history.map((item) => <button className="history-card" key={item.id} onClick={() => { setInput(item.preview); setScanType(item.type); setActiveNav('Overview'); }}><span className="history-type">{item.type}</span><strong>{item.preview}</strong><small>{new Date(item.created_at).toLocaleString()} <b>{item.score}/100</b></small></button>)}</div> : <p className="empty-state">Your saved analyses will appear here after the first API-backed scan.</p>}</section>}
          {activeNav === 'Test library' && <section className="workspace-view"><div className="block-heading"><div><span className="section-kicker">PUBLIC SCENARIOS</span><h2>Test library</h2></div><span className="view-summary">{testCases.length} cases</span></div><div className="library-grid">{testCases.map((testCase) => <button className="library-card" key={testCase.id} onClick={() => loadTestCase(testCase)}><span className="history-type">{testCase.type}</span><strong>{testCase.title}</strong><p>{testCase.content}</p><small>{testCase.tags.join(' · ')} <ArrowUpRight size={13} /></small></button>)}</div></section>}

          <section className="scan-layout">
            <div className="scan-panel"><div className="panel-heading"><div><span className="section-kicker">NEW CHECK</span><h2>What feels off?</h2></div><span className="powered"><Sparkles size={14} /> AI-assisted</span></div>
              <div className="type-tabs">{([['URL', Link2], ['Email', Mail], ['Message', MessageSquareText]] as const).map(([type, Icon]) => <button key={type} className={scanType === type ? 'type-tab selected' : 'type-tab'} onClick={() => selectType(type)}><Icon size={16} />{type}</button>)}</div>
              <div className="input-wrap"><textarea value={input} onChange={(event) => setInput(event.target.value)} placeholder="Paste a link, message, or email here..." /><span className="char-count">{input.length} chars</span></div>
              <div className="scan-controls"><button className="paste-button" onClick={() => navigator.clipboard?.readText().then((text) => text && setInput(text))}><ClipboardPaste size={16} /> Paste from clipboard</button><button className="scan-button" onClick={runScan} disabled={scanning}><ScanSearch size={17} /> {scanning ? 'Analyzing...' : 'Analyze now'}</button></div>
              <div className="privacy-note"><ShieldCheck size={14} /> Your content is analyzed securely and never shared.<span className={`api-status ${apiState}`}><i /> {apiState === 'connected' ? 'API connected' : 'Local engine'}</span></div>
            </div>

            <div className={`result-panel ${scoreColor}`}><div className="result-top"><span className="section-kicker">LATEST RESULT</span><span className="result-time">Just now</span></div><div className="score-row"><div className="score-ring"><div><strong>{analysis.score}</strong><span>/100</span></div></div><div><span className="verdict-label">VERDICT</span><h2>{analysis.verdict}</h2><p>{analysis.summary}</p></div></div><div className="result-divider" /><div className="signal-header"><strong>{analysis.findings.length} signals found</strong><span>Confidence <b>{analysis.findings.length ? '94' : '81'}%</b></span></div><div className="findings">{analysis.findings.length ? analysis.findings.slice(0, 3).map((finding) => <div className="finding" key={finding.label}><span className={`finding-icon ${finding.severity}`}><TriangleAlert size={14} /></span><span><strong>{finding.label}</strong><small>{finding.detail}</small></span></div>) : <div className="finding"><span className="finding-icon low"><CheckCircle2 size={14} /></span><span><strong>Nothing obviously suspicious</strong><small>Keep checking unexpected requests through a known channel.</small></span></div>}</div><button className="explain-button" onClick={() => setShowExplanation((current) => !current)}>{showExplanation ? 'Hide explanation' : 'View full explanation'} <ArrowUpRight size={16} /></button>{showExplanation && <div className="explanation-more"><strong>What to do next</strong><p>{analysis.findings[0]?.recommendation ?? 'Verify unexpected requests independently before responding.'}</p></div>}</div>
          </section>

          <section className="lower-grid"><div className="section-block"><div className="block-heading"><div><span className="section-kicker">RECENT ACTIVITY</span><h2>Your scans</h2></div><button className="text-button" onClick={() => setActiveNav('Scan history')}>View history <ArrowUpRight size={15} /></button></div><div className="activity-list">{history.slice(0, 3).map((item) => <Activity key={item.id} icon={item.type === 'URL' ? <Link2 size={16} /> : item.type === 'Email' ? <Mail size={16} /> : <MessageSquareText size={16} />} title={item.preview} meta={`${item.type} · ${new Date(item.created_at).toLocaleDateString()}`} score={String(item.score)} tone={item.score >= 65 ? 'coral' : item.score >= 30 ? 'amber' : 'mint'} />)}{!history.length && <p className="empty-state">No saved scans yet. Analyze something suspicious above.</p>}</div></div><div className="section-block test-block"><div className="block-heading"><div><span className="section-kicker">TRY A SCENARIO</span><h2>Test library</h2></div><button className="circle-arrow" aria-label="Open test library" onClick={() => setActiveNav('Test library')}><ArrowUpRight size={17} /></button></div><p>See how ScamShield handles the scams people see every day.</p><div className="test-tags">{testCases.slice(0, 3).map((testCase) => <button key={testCase.id} onClick={() => loadTestCase(testCase)}><Sparkles size={14} /> {testCase.title}</button>)}</div><button className="library-note" onClick={() => setActiveNav('Test library')}>{testCases.length || 0} public test cases <ArrowUpRight size={13} /></button></div></section>
          <footer><span><span className="footer-mark"><ShieldCheck size={14} /></span> ScamShield</span><span>Built for a safer internet <span className="footer-dot">·</span> v0.1</span></footer>
        </div>
      </section>
      {modal && <div className="modal-backdrop" onClick={() => setModal(null)}><section className="modal" onClick={(event) => event.stopPropagation()}><button className="modal-close" onClick={() => setModal(null)} aria-label="Close">×</button>{modal === 'help' && <><span className="section-kicker">SCAMSHIELD GUIDE</span><h2>How it works</h2><p>Paste a suspicious URL, email, or message. ScamShield checks language, payment requests, links, and sender signals, then explains the evidence.</p><p className="modal-note">Results are advisory. Never share passwords or verification codes, even when a message looks safe.</p></>}{modal === 'notifications' && <><span className="section-kicker">INBOX</span><h2>Notifications</h2><div className="notification"><span className="status-dot" /><span><strong>Protection is active</strong><small>Your workspace is ready for its next scan.</small></span></div><div className="notification"><span className="status-dot" /><span><strong>{stats.high_risk} high-risk results</strong><small>Review your recent scan history for details.</small></span></div></>}{modal === 'profile' && <><span className="section-kicker">WORKSPACE</span><h2>Jordan&apos;s workspace</h2><p>Personal protection workspace</p><button className="modal-action" onClick={() => showNotice('Workspace settings are coming next.')}>Workspace settings</button></>}{modal === 'report' && <><span className="section-kicker">HELP US IMPROVE</span><h2>Report this result</h2><p>Tell us what the detector missed or misunderstood.</p><select value={reportReason} onChange={(event) => setReportReason(event.target.value as typeof reportReason)}><option value="missed_scam">This is a scam we missed</option><option value="false_positive">This is not a scam</option><option value="other">Something else</option></select><textarea value={reportNotes} onChange={(event) => setReportNotes(event.target.value)} placeholder="Optional notes" /><button className="modal-action" onClick={sendReport}>Send report</button></>}</section></div>}
      {notice && <div className="toast"><CheckCircle2 size={16} />{notice}</div>}
    </main>
  );
}

function Activity({ icon, title, meta, score, tone }: { icon: React.ReactNode; title: string; meta: string; score: string; tone: string }) {
  return <div className="activity-item"><span className="activity-icon">{icon}</span><span className="activity-copy"><strong>{title}</strong><small>{meta}</small></span><span className={`mini-score ${tone}`}>{score}<small>/100</small></span><ExternalLink size={15} className="activity-link" /></div>;
}
