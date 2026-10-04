import React, { useEffect, useState } from 'react'
import { supabase } from '../supabaseClient.js'

export default function FaultAlerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)

      // Get the latest sensor reading per machine
      const { data: sensorData } = await supabase
        .from('sensor_readings')
        .select('machine_id, vibration, timestamp')
        .order('timestamp', { ascending: false })
        .limit(200)

      // Get the latest twin prediction per machine
      const { data: predData } = await supabase
        .from('twin_predictions')
        .select('machine_id, expected_vibration, timestamp')
        .order('timestamp', { ascending: false })
        .limit(200)

      if (!sensorData || !predData) {
        setLoading(false)
        return
      }

      // Find latest reading per machine
      const latestSensor = {}
      sensorData.forEach((r) => {
        if (!latestSensor[r.machine_id] || new Date(r.timestamp) > new Date(latestSensor[r.machine_id].timestamp)) {
          latestSensor[r.machine_id] = r
        }
      })

      // Find latest prediction per machine
      const latestPred = {}
      predData.forEach((p) => {
        if (!latestPred[p.machine_id] || new Date(p.timestamp) > new Date(latestPred[p.machine_id].timestamp)) {
          latestPred[p.machine_id] = p
        }
      })

      // Build alert data
      const allMachines = new Set([...Object.keys(latestSensor), ...Object.keys(latestPred)])
      const alertList = []

      allMachines.forEach((machine) => {
        const sensor = latestSensor[machine]
        const pred = latestPred[machine]

        if (sensor && pred && Number(pred.expected_vibration) > 0) {
          const actual = Number(sensor.vibration)
          const expected = Number(pred.expected_vibration)
          const deviation = ((actual - expected) / expected) * 100

          alertList.push({
            machine_id: machine,
            actual,
            expected,
            deviation,
            isFault: deviation > 15,
            timestamp: sensor.timestamp,
          })
        } else if (sensor) {
          alertList.push({
            machine_id: machine,
            actual: Number(sensor.vibration),
            expected: null,
            deviation: 0,
            isFault: false,
            timestamp: sensor.timestamp,
          })
        }
      })

      // Sort worst deviation first
      alertList.sort((a, b) => b.deviation - a.deviation)
      setAlerts(alertList)
      setLoading(false)
    }

    fetchData()
  }, [])

  // KPI: number of active faults
  const faultCount = alerts.filter((a) => a.isFault).length
  const worstDeviation = alerts.length > 0 ? alerts[0].deviation : 0

  if (loading) return <div className="loading-spinner">Analyzing vibration data…</div>

  return (
    <div id="fault-alerts-page">
      <div className="page-header">
        <h2>Fault Alerts</h2>
        <p>Vibration deviation analysis — machines exceeding 15% threshold are flagged</p>
      </div>

      {/* KPI */}
      <div className="kpi-card" id="kpi-fault-count" style={{
        borderImage: faultCount > 0
          ? 'linear-gradient(180deg, #ef4444, #f59e0b) 1'
          : 'linear-gradient(180deg, #10b981, #34d399) 1'
      }}>
        <div className="kpi-icon" style={{
          background: faultCount > 0
            ? 'linear-gradient(135deg, #ef4444, #f59e0b)'
            : 'linear-gradient(135deg, #10b981, #34d399)'
        }}>
          {faultCount > 0 ? '⚠' : '✓'}
        </div>
        <div className="kpi-content">
          <h3>Active Fault Alerts</h3>
          <span className="kpi-value" style={{
            background: faultCount > 0
              ? 'linear-gradient(135deg, #ef4444, #f59e0b)'
              : 'linear-gradient(135deg, #10b981, #34d399)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            {faultCount}
          </span>
          <span className="kpi-unit">
            {faultCount > 0 ? `/ worst at ${worstDeviation.toFixed(1)}% deviation` : 'All systems normal'}
          </span>
        </div>
      </div>

      {/* Alert Cards */}
      {alerts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📡</div>
          <p>No sensor or prediction data available yet.</p>
        </div>
      ) : (
        <div id="alert-list">
          {alerts.map((alert) => (
            <div
              key={alert.machine_id}
              className={`alert-card ${alert.isFault ? '' : 'normal'}`}
              id={`alert-${alert.machine_id}`}
            >
              <div className={`alert-icon ${alert.isFault ? 'danger' : 'success'}`}>
                {alert.isFault ? '⚠' : '✓'}
              </div>
              <div>
                <h4>{alert.machine_id}</h4>
                {alert.isFault ? (
                  <p>
                    Vibration is <strong>{alert.deviation.toFixed(1)}%</strong> above expected
                    (actual: {alert.actual.toFixed(2)} vs expected: {alert.expected?.toFixed(2)})
                    since {new Date(alert.timestamp).toLocaleString()}.
                  </p>
                ) : (
                  <p>
                    Operating within normal parameters.
                    {alert.expected !== null
                      ? ` Deviation: ${alert.deviation.toFixed(1)}%`
                      : ' No prediction baseline available.'}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
