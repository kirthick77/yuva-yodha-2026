import React, { useEffect, useState, useRef } from 'react'
import { supabase } from '../supabaseClient.js'
import jsPDF from 'jspdf'
import 'jspdf-autotable'

export default function AuditReport() {
  const [auditData, setAuditData] = useState([])
  const [loading, setLoading] = useState(true)
  const tableRef = useRef(null)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      const { data } = await supabase
        .from('audit_results')
        .select('*')
        .order('priority_rank', { ascending: true })

      if (data) setAuditData(data)
      setLoading(false)
    }
    fetchData()
  }, [])

  // KPI: count of machines exceeding BEE benchmark
  const exceedCount = auditData.filter((a) => Number(a.sec_actual) > Number(a.sec_bee_benchmark)).length

  const handleDownloadPDF = () => {
    const doc = new jsPDF()

    doc.setFontSize(18)
    doc.setTextColor(15, 42, 74)
    doc.text('Energy Audit Report', 14, 22)

    doc.setFontSize(10)
    doc.setTextColor(107, 114, 128)
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 30)

    const tableData = auditData.map((row) => [
      row.priority_rank,
      row.machine_id,
      Number(row.sec_actual).toFixed(2),
      Number(row.sec_bee_benchmark).toFixed(2),
      row.recommended_action || '-',
    ])

    doc.autoTable({
      startY: 38,
      head: [['Rank', 'Machine', 'Actual SEC', 'BEE Benchmark', 'Recommended Action']],
      body: tableData,
      theme: 'striped',
      headStyles: { fillColor: [15, 42, 74], fontSize: 9 },
      bodyStyles: { fontSize: 8.5 },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      didParseCell: function (data) {
        if (data.section === 'body') {
          const rowIndex = data.row.index
          const row = auditData[rowIndex]
          if (row && Number(row.sec_actual) > Number(row.sec_bee_benchmark)) {
            data.cell.styles.fillColor = [254, 226, 226]
          }
        }
      },
      margin: { left: 14, right: 14 },
    })

    doc.save('energy-audit-report.pdf')
  }

  if (loading) return <div className="loading-spinner">Loading audit data…</div>

  return (
    <div id="audit-page">
      <div className="page-header">
        <h2>Audit Report</h2>
        <p>Specific Energy Consumption analysis against BEE benchmarks</p>
      </div>

      {/* KPI */}
      <div className="kpi-card" id="kpi-audit-exceed" style={{
        borderImage: exceedCount > 0
          ? 'linear-gradient(180deg, #ef4444, #f59e0b) 1'
          : 'linear-gradient(180deg, #10b981, #34d399) 1'
      }}>
        <div className="kpi-icon" style={{
          background: exceedCount > 0
            ? 'linear-gradient(135deg, #ef4444, #f59e0b)'
            : 'linear-gradient(135deg, #10b981, #34d399)'
        }}>
          📋
        </div>
        <div className="kpi-content">
          <h3>Machines Exceeding BEE Benchmark</h3>
          <span className="kpi-value" style={{
            background: exceedCount > 0
              ? 'linear-gradient(135deg, #ef4444, #f59e0b)'
              : 'linear-gradient(135deg, #10b981, #34d399)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            {exceedCount}
          </span>
          <span className="kpi-unit">of {auditData.length} total machines</span>
        </div>
      </div>

      {/* Download Button */}
      <div style={{ marginBottom: 20 }}>
        <button className="btn btn-primary" onClick={handleDownloadPDF} id="btn-download-pdf">
          <span>📄</span> Download as PDF
        </button>
      </div>

      {auditData.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <p>No audit results available.</p>
        </div>
      ) : (
        <div className="card" id="audit-table-card">
          <table className="data-table" ref={tableRef} id="audit-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Machine</th>
                <th>Actual SEC</th>
                <th>BEE Benchmark SEC</th>
                <th>Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              {auditData.map((row) => {
                const exceeds = Number(row.sec_actual) > Number(row.sec_bee_benchmark)
                return (
                  <tr key={row.id} className={exceeds ? 'row-warning' : ''}>
                    <td>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 28,
                        height: 28,
                        borderRadius: 6,
                        background: '#f1f5f9',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                      }}>
                        {row.priority_rank}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{row.machine_id}</td>
                    <td>
                      <span style={{ color: exceeds ? '#ef4444' : '#10b981', fontWeight: 600 }}>
                        {Number(row.sec_actual).toFixed(2)}
                      </span>
                    </td>
                    <td>{Number(row.sec_bee_benchmark).toFixed(2)}</td>
                    <td style={{ maxWidth: 320, fontSize: '0.84rem' }}>{row.recommended_action || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
