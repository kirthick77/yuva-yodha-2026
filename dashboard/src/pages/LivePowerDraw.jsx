import React, { useEffect, useState, useRef } from 'react'
import { supabase } from '../supabaseClient.js'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const MACHINE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4', '#84cc16']

export default function LivePowerDraw() {
  const [readings, setReadings] = useState([])
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(true)
  const readingsRef = useRef([])

  // Fetch initial data
  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      const [readingsRes, predictionsRes] = await Promise.all([
        supabase
          .from('sensor_readings')
          .select('*')
          .order('timestamp', { ascending: false })
          .limit(50),
        supabase
          .from('twin_predictions')
          .select('*')
          .order('timestamp', { ascending: false })
          .limit(50),
      ])

      if (readingsRes.data) {
        readingsRef.current = readingsRes.data
        setReadings(readingsRes.data)
      }
      if (predictionsRes.data) setPredictions(predictionsRes.data)
      setLoading(false)
    }
    fetchData()
  }, [])

  // Subscribe to realtime inserts
  useEffect(() => {
    const channel = supabase
      .channel('sensor_readings_realtime')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'sensor_readings' },
        (payload) => {
          readingsRef.current = [payload.new, ...readingsRef.current].slice(0, 100)
          setReadings([...readingsRef.current])
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  // Derive machines and chart data
  const machines = [...new Set(readings.map((r) => r.machine_id))]
  const predMap = {}
  predictions.forEach((p) => {
    const key = `${p.machine_id}_${p.timestamp}`
    predMap[key] = p.expected_power
  })

  // Build time-series data: group by timestamp
  const timeMap = {}
  readings.forEach((r) => {
    const t = r.timestamp
    if (!timeMap[t]) timeMap[t] = { timestamp: t }
    timeMap[t][`${r.machine_id}_actual`] = Number(r.power_kw)
    const predKey = `${r.machine_id}_${t}`
    if (predMap[predKey] !== undefined) {
      timeMap[t][`${r.machine_id}_expected`] = Number(predMap[predKey])
    }
  })

  // Also add predictions that may not have a matching reading timestamp
  predictions.forEach((p) => {
    const t = p.timestamp
    if (!timeMap[t]) timeMap[t] = { timestamp: t }
    timeMap[t][`${p.machine_id}_expected`] = Number(p.expected_power)
  })

  const chartData = Object.values(timeMap)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

  // KPI: sum of latest reading per machine
  const latestPerMachine = {}
  readings.forEach((r) => {
    if (!latestPerMachine[r.machine_id] || new Date(r.timestamp) > new Date(latestPerMachine[r.machine_id].timestamp)) {
      latestPerMachine[r.machine_id] = r
    }
  })
  const totalPower = Object.values(latestPerMachine).reduce((s, r) => s + Number(r.power_kw), 0)

  if (loading) return <div className="loading-spinner">Loading sensor data…</div>

  return (
    <div id="live-power-page">
      <div className="page-header">
        <h2>Live Power Draw</h2>
        <p>Real-time power consumption across all factory machines</p>
      </div>

      {/* KPI */}
      <div className="kpi-card" id="kpi-total-power">
        <div className="kpi-icon">⚡</div>
        <div className="kpi-content">
          <h3>Total Current Power Draw</h3>
          <span className="kpi-value">{totalPower.toFixed(1)}</span>
          <span className="kpi-unit">kW</span>
        </div>
      </div>

      {/* Chart */}
      <div className="card" id="power-chart-card">
        {chartData.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📊</div>
            <p>No sensor readings yet. Data will appear as readings arrive.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={420}>
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(v) => {
                  const d = new Date(v)
                  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
                }}
                fontSize={12}
              />
              <YAxis fontSize={12} label={{ value: 'kW', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }} />
              <Tooltip
                labelFormatter={(v) => new Date(v).toLocaleString()}
                contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 2px 12px rgba(0,0,0,0.1)' }}
              />
              <Legend />
              {machines.map((m, i) => (
                <React.Fragment key={m}>
                  <Line
                    type="monotone"
                    dataKey={`${m}_actual`}
                    name={`${m} (Actual)`}
                    stroke={MACHINE_COLORS[i % MACHINE_COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey={`${m}_expected`}
                    name={`${m} (Expected)`}
                    stroke={MACHINE_COLORS[i % MACHINE_COLORS.length]}
                    strokeWidth={1.5}
                    strokeDasharray="6 4"
                    dot={false}
                    opacity={0.6}
                  />
                </React.Fragment>
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
