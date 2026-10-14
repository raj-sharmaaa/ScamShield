export async function detect(text: string): Promise<{ is_scam: boolean }> {
  const res = await fetch('/api/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })

  if (!res.ok) throw new Error('network')
  return res.json()
}
