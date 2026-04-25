// frontend/src/components/ExportButtons.tsx
import { exportPdfUrl, exportCsvUrl } from '../api/client'

export function ExportButtons({ sessionId }: { sessionId: string }) {
  return (
    <div style={{ display: 'flex', gap: 10, margin: '16px 0' }}>
      <a href={exportPdfUrl(sessionId)} download style={linkBtnStyle('#333', 'white')}>
        Download PDF
      </a>
      <a href={exportCsvUrl(sessionId)} download style={linkBtnStyle('white', '#333')}>
        Download CSV
      </a>
    </div>
  )
}

function linkBtnStyle(bg: string, color: string): React.CSSProperties {
  return {
    padding: '8px 18px', background: bg, color, border: `1px solid #333`,
    borderRadius: 6, textDecoration: 'none', fontSize: 13, fontWeight: 'bold',
  }
}
