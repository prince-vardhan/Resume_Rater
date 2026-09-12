function FilePicker({ id, label, hint, accept, multiple, files, onChange }) {
  const count = files ? files.length : 0

  return (
    <label className="file-picker" htmlFor={id}>
      <div className="file-picker-text">
        <span className="file-picker-label">{label}</span>
        <span className="file-picker-hint">{hint}</span>
      </div>
      <div className="file-picker-status">
        {count === 0 ? (
          <span className="file-picker-placeholder">Choose file{multiple ? 's' : ''}</span>
        ) : multiple ? (
          <span className="pill pill-accent">{count} file{count === 1 ? '' : 's'} selected</span>
        ) : (
          <span className="pill pill-accent">{files[0].name}</span>
        )}
      </div>
      <input
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={(e) => onChange(Array.from(e.target.files || []))}
        hidden
      />
    </label>
  )
}

export default function UploadForm({
  jdFile,
  resumeFiles,
  onJdChange,
  onResumesChange,
  onRun,
  loading,
}) {
  const canRun = Boolean(jdFile) && resumeFiles.length > 0 && !loading

  return (
    <section className="card upload-card">
      <h2>1. Upload</h2>
      <div className="upload-grid">
        <FilePicker
          id="jd-upload"
          label="Job description"
          hint="One PDF"
          accept="application/pdf"
          multiple={false}
          files={jdFile ? [jdFile] : []}
          onChange={(files) => onJdChange(files[0] || null)}
        />
        <FilePicker
          id="resume-upload"
          label="Resumes"
          hint="Multiple PDFs (15-18 typical)"
          accept="application/pdf"
          multiple
          files={resumeFiles}
          onChange={onResumesChange}
        />
      </div>
      <button className="btn btn-primary run-btn" onClick={onRun} disabled={!canRun}>
        {loading ? 'Ranking…' : 'Run ranking'}
      </button>
    </section>
  )
}
