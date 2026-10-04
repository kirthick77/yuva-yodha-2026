import React, { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

export default function CarbonReport() {
  const [emissions, setEmissions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      const { data } = await supabase
        .from('emissions_log')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(500)

      if (data) setEmissions(data)
      setLoading(false)
    }
    fetchData()
  }, [])

  // Group by day
  const dayMap = {}
  emissions.forEach((e) => {
    const day = new Date(e.timestamp).toISOString().slice(0, 10)
    if (!dayMap[day]) dayMap[day] = { day, grid_kwh: 0, solar_kwh: 0, co2_kg: 0 }
    dayMap[day].grid_kwh += Number(e.grid_kwh) || 0
    dayMap[day].solar_kwh += Number(e.solar_kwh) || 0
    dayMap[day].co2_kg += Number(e.co2_kg) || 0
  })

  const dailyData = Object.values(dayMap)
    .sort((a, b) => a.day.localeCompare(b.day))
    .slice(-7)

  // Today's data
  const todayStr = new Date().toISOString().slice(0, 10)
  const todayData = dayMap[todayStr] || { grid_kwh: 0, solar_kwh: 0, co2_kg: 0 }
  const todayTotal = todayData.grid_kwh + todayData.solar_kwh
  const solarPct = todayTotal > 0 ? ((todayData.solar_kwh / todayTotal) * 100).toFixed(1) : '0.0'
  const gridPct = todayTotal > 0 ? ((todayData.grid_kwh / todayTotal) * 100).toFixed(1) : '0.0'

  // KPI: today's total CO2
  const todayCO2 = todayData.co2_kg

  if (loading) return <div className="loading-spinner">Loading emissions data…</div>

  return (
    <div id="carbon-page">
      <div className="page-header">
        <h2>Carbon Report</h2>
        <p>Grid vs. solar energy consumption and CO₂ emissions tracking</p>
      </div>

      {/* KPI */}
      <div className="kpi-card" id="kpi-co2-today" style={{
        borderImage: 'linear-gradient(180deg, #10b981, #34d399) 1'
      }}>
        <div className="kpi-icon" style={{ background: 'linear-gradient(135deg, #10b981, #34d399)' }}>
          🌿
        </div>
        <div className="kpi-content">
          <h3>Today's CO₂ Emissions</h3>
          <span className="kpi-value" style={{
            background: 'linear-gradient(135deg, #10b981, #34d399)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            {todayCO2.toFixed(1)}
          </span>
          <span className="kpi-unit">kg CO₂</span>
        </div>
      </div>

      {/* Chart */}
      {dailyData.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🌿</div>
          <p>No emissions data available yet.</p>
        </div>
      ) : (
        <div className="card" id="carbon-chart-card">
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={dailyData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="day"
                tickFormatter={(v) => {
                  const d = new Date(v + 'T00:00:00')
                  return `${d.getMonth() + 1}/${d.getDate()}`
                }}
                fontSize={12}
              />
              <YAxis fontSize={12} label={{ value: 'kWh', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 2px 12px rgba(0,0,0,0.1)' }}
                formatter={(value, name) => [`${Number(value).toFixed(1)} kWh`, name]}
              />
              <Legend />
              <Bar dataKey="grid_kwh" name="Grid (kWh)" stackId="energy" fill="#6366f1" radius={[0, 0, 0, 0]} />
              <Bar dataKey="solar_kwh" name="Solar (kWh)" stackId="energy" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>

          {/* Caption */}
          <div className="chart-caption" id="energy-source-caption">
            Today's energy mix: <strong style={{ color: '#10b981' }}>{solarPct}% solar</strong> and{' '}
            <strong style={{ color: '#6366f1' }}>{gridPct}% grid</strong>.
            {Number(solarPct) > 50
              ? ' Great — the majority of today\'s energy is from renewable sources! ☀️'
              : Number(solarPct) > 0
                ? ' Increasing solar utilization can further reduce carbon footprint.'
                : ''}
          </div>
        </div>
      )}
    </div>
  )
}
