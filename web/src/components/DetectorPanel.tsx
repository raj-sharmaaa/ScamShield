import React, { useState } from 'react'
import { detect } from '../utils/api'
import '../styles.css'

export default function DetectorPanel() {
  const [text, setText] = useState('')
  const [result, setResult] = useState<string | null>(null)

  async function onCheck() {
    try {
      const res = await detect(text)
      setResult(res.is_scam ? 'Likely scam' : 'Looks okay')
    } catch (err) {
      setResult('API unreachable (demo)')
    }
  }

  return (
    <div className="panel">
      <textarea value={text} onChange={e => setText(e.target.value)} placeholder="Paste suspicious text" />
      <button onClick={onCheck}>Check</button>
      {result && <div className="result">{result}</div>}
    </div>
  )
}
