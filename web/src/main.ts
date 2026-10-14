// Minimal TypeScript entry for a tiny web UI (no framework required)
import './styles.css'

const root = document.getElementById('root') || document.body;

const title = document.createElement('h1');
title.textContent = 'ScamShield — Demo UI';
root.appendChild(title);

const textarea = document.createElement('textarea');
textarea.placeholder = 'Paste a suspicious message here...';
textarea.rows = 6;
textarea.cols = 60;
root.appendChild(textarea);

const btn = document.createElement('button');
btn.textContent = 'Check';
btn.onclick = async () => {
  const text = textarea.value;
  // Demo: call local API /api/detect (not implemented here)
  try {
    const res = await fetch('/api/detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const json = await res.json();
    alert(json.is_scam ? 'Likely scam' : 'Looks ok');
  } catch (err) {
    alert('Could not contact API (demo)');
  }
};
root.appendChild(btn);
