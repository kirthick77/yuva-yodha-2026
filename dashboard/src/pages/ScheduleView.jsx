import React, { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient.js'

const TARIFF_COLORS = {
  cheap: 'tariff-cheap',
  mid: 'tariff-mid',
  expensive: 'tariff-expensive',
}

const TARIFF_LABELS = {
  cheap: 'Off-Peak (Cheap)',
  mid: 'Mid-Peak',
  expensive: 'Peak (Expensive)',
}

export default function ScheduleView() {
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      const { data } = await supabase
        .from('schedules')
        .select('*')
        .order('scheduled_start', { ascending: true })

      if (data) setSchedules(data)
      setLoading(false)
    }
    fetchData()
  }, [])

  // Group by machine
  const machineMap = {}
  schedules.forEach((s) => {
    if (!machineMap[s.machine_id]) machineMap[s.machine_id] = []
    machineMap[s.machine_id].push(s)
  })

  // Find overall time range
  const allStarts = schedules.map((s) => new Date(s.scheduled_start).getTime())
  const allEnds = schedules.map((s) => new Date(s.scheduled_end).getTime())
  const minTime = allStarts.length > 0 ? Math.min(...allStarts) : 0
  const maxTime = allEnds.length > 0 ? Math.max(...allEnds) : 1
  const totalSpan = maxTime - minTime || 1

  // KPI: total scheduled hours
  const totalHours = schedules.reduce((sum, s) => {
    const dur = (new Date(s.scheduled_end) - new Date(s.scheduled_start)) / (1000 * 60 * 60)
    return sum + dur
  }, 0)

  // Generate time axis labels
  const timeLabels = []
  if (schedules.length > 0) {
    const step = totalSpan / 6
    for (let i = 0; i <= 6; i++) {
      const d = new Date(minTime + step * i)
      timeLabels.push({
        label: `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`,
        pct: (i / 6) * 100,
      })
    }
  }

  if (loading) return <div className="loading-spinner">Loading schedules…</div>

  return (
    <div id="schedule-page">
      <div className="page-header">
        <h2>Schedule View</h2>
        <p>Machine operation schedule with tariff band visualization</p>
      </div>

      {/* KPI */}
      <div className="kpi-card" id="kpi-schedule-hours">
        <div className="kpi-icon">📅</div>
        <div className="kpi-content">
          <h3>Total Scheduled Runtime</h3>
          <span className="kpi-value">{totalHours.toFixed(1)}</span>
          <span className="kpi-unit">hours</span>
        </div>
      </div>

      {schedules.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📅</div>
          <p>No schedules found.</p>
        </div>
      ) : (
        <div className="card" id="gantt-card">
          {/* Legend */}
          <div className="gantt-legend">
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }} />
              <span>Off-Peak (Cheap)</span>
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: 'linear-gradient(135deg, #f59e0b, #fbbf24)' }} />
              <span>Mid-Peak</span>
            </div>
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: 'linear-gradient(135deg, #ef4444, #f87171)' }} />
              <span>Peak (Expensive)</span>
            </div>
            <div className="legend-item">
              <span>☀️ = Solar Available</span>
            </div>
          </div>

          {/* Time Axis */}
          <div style={{ display: 'flex', marginLeft: 140, marginBottom: 8, position: 'relative', height: 20 }}>
            {timeLabels.map((tl, i) => (
              <span
                key={i}
                style={{
                  position: 'absolute',
                  left: `${tl.pct}%`,
                  transform: 'translateX(-50%)',
                  fontSize: '0.68rem',
                  color: '#9ca3af',
                  whiteSpace: 'nowrap',
                }}
              >
                {tl.label}
              </span>
            ))}
          </div>

          {/* Gantt Rows */}
          <div className="gantt-container">
            {Object.entries(machineMap).map(([machine, items]) => (
              <div className="gantt-row" key={machine}>
                <div className="gantt-label">{machine}</div>
                <div className="gantt-track">
                  {items.map((item) => {
                    const start = new Date(item.scheduled_start).getTime()
                    const end = new Date(item.scheduled_end).getTime()
                    const left = ((start - minTime) / totalSpan) * 100
                    const width = ((end - start) / totalSpan) * 100
                    const band = (item.tariff_band || 'mid').toLowerCase()
                    const tariffClass = TARIFF_COLORS[band] || 'tariff-mid'

                    return (
                      <div
                        key={item.id}
                        className={`gantt-bar ${tariffClass}`}
                        style={{ left: `${left}%`, width: `${Math.max(width, 1.5)}%` }}
                        title={`${item.tariff_band} | ${new Date(item.scheduled_start).toLocaleString()} → ${new Date(item.scheduled_end).toLocaleString()}`}
                      >
                        {item.solar_available && <span className="sun-badge">☀️</span>}
                        {width > 8 && <span style={{ fontSize: '0.65rem', marginLeft: 2 }}>{item.tariff_band}</span>}
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
