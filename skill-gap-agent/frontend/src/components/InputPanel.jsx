import { useState, useRef, useCallback } from 'react'

async function extractTextFromFile(file) {
  const ext = file.name.split('.').pop().toLowerCase()

  if (ext === 'txt' || ext === 'md') {
    return await file.text()
  }

  if (ext === 'pdf') {
    if (!window.pdfjsLib) throw new Error('PDF library not loaded yet — please try again in a moment.')
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await window.pdfjsLib.getDocument({ data: new Uint8Array(arrayBuffer) }).promise
    let text = ''
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const content = await page.getTextContent()
      text += content.items.map(item => item.str).join(' ') + '\n'
    }
    return text.trim()
  }

  if (ext === 'docx') {
    if (!window.mammoth) throw new Error('DOCX library not loaded yet — please try again in a moment.')
    const arrayBuffer = await file.arrayBuffer()
    const result = await window.mammoth.extractRawText({ arrayBuffer })
    return result.value.trim()
  }

  throw new Error(`Unsupported file type: .${ext}. Use .pdf, .docx, or .txt`)
}

export default function InputPanel({ onStart, loading, error }) {
  const [jdText, setJdText] = useState('')
  const [resumeText, setResumeText] = useState('')
  const [resumeFileName, setResumeFileName] = useState('')
  const [dragging, setDragging] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [parseError, setParseError] = useState(null)
  const [showPaste, setShowPaste] = useState(false)
  const fileRef = useRef(null)

  const processFile = useCallback(async (file) => {
    setParseError(null)
    setParsing(true)
    try {
      const text = await extractTextFromFile(file)
      setResumeText(text)
      setResumeFileName(file.name)
      setShowPaste(false)
    } catch (err) {
      setParseError(err.message)
    } finally {
      setParsing(false)
    }
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) processFile(file)
  }, [processFile])

  const handleFileInput = (e) => {
    const file = e.target.files?.[0]
    if (file) processFile(file)
    e.target.value = ''
  }

  const clearResume = () => {
    setResumeText('')
    setResumeFileName('')
    setParseError(null)
    setShowPaste(false)
  }

  const canSubmit = jdText.trim() && resumeText.trim() && !loading && !parsing

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!canSubmit) return
    onStart({ jdText: jdText.trim(), resumeText: resumeText.trim() })
  }

  return (
    <div className="input-page">
      <div className="input-card">
        <div className="input-header">
          <div className="input-logo-mark">✦</div>
          <h1 className="input-title">Skill Gap Agent</h1>
          <p className="input-subtitle">
            Paste a job description and upload your resume. The agent will
            interview you, identify gaps, and build a personalised learning plan.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="input-form">
          <div className="fields-row">
            {/* JD */}
            <div className="field-group">
              <label className="field-label">Job Description</label>
              <textarea
                className="field-textarea"
                placeholder="Paste the full job description here…"
                value={jdText}
                onChange={e => setJdText(e.target.value)}
                rows={12}
              />
              <span className="field-chars">{jdText.length} chars</span>
            </div>

            {/* Resume */}
            <div className="field-group">
              <label className="field-label">Candidate Resume</label>

              {/* Drop zone */}
              {!resumeFileName ? (
                <div
                  className={`drop-zone ${dragging ? 'dragging' : ''}`}
                  onDragOver={e => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => fileRef.current?.click()}
                >
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".txt,.pdf,.docx,.md"
                    style={{ display: 'none' }}
                    onChange={handleFileInput}
                  />
                  <div className="drop-icon">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                      <path d="M12 16V8m0 0-3 3m3-3 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M20 16.7A4 4 0 0 0 18 9h-1.26A8 8 0 1 0 4 16.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <p className="drop-primary">Drop your resume here</p>
                  <p className="drop-secondary">or click to browse — PDF, DOCX, TXT</p>
                </div>
              ) : (
                <div className="drop-success">
                  <div className="drop-success-info">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path d="M3 8l3.5 3.5L13 4" stroke="#22c55e" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span className="drop-filename">{resumeFileName}</span>
                    <span className="drop-chars">{resumeText.length.toLocaleString()} chars</span>
                  </div>
                  <button type="button" className="drop-clear" onClick={clearResume}>
                    ×
                  </button>
                </div>
              )}

              {parsing && <p className="parse-status">Extracting text…</p>}
              {parseError && <p className="parse-error">{parseError}</p>}

              {/* Paste fallback */}
              <button
                type="button"
                className="paste-toggle"
                onClick={() => setShowPaste(v => !v)}
              >
                {showPaste ? '− Hide' : '+ Paste text instead'}
              </button>

              {showPaste && (
                <div style={{ position: 'relative' }}>
                  <textarea
                    className="field-textarea"
                    placeholder="Paste resume text here…"
                    value={resumeText}
                    onChange={e => {
                      setResumeText(e.target.value)
                      setResumeFileName('')
                    }}
                    rows={8}
                  />
                  <span className="field-chars">{resumeText.length} chars</span>
                </div>
              )}
            </div>
          </div>

          {(error) && <div className="error-banner">{error}</div>}

          <button type="submit" className="start-btn" disabled={!canSubmit}>
            {loading ? (
              <span className="btn-loading">
                <span className="spinner" /> Starting assessment…
              </span>
            ) : (
              'Start Assessment →'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
