// src/components/SeoTrendChart.jsx
import React from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(LineElement, CategoryScale, LinearScale, PointElement, Tooltip, Legend);

function SeoTrendChart({ trendData }) {
  const chartData = {
    labels: trendData.map((_, i) => `Run ${i + 1}`),
    datasets: [
      {
        label: "SEO Score Trend",
        data: trendData,
        borderColor: "#007bff",
        backgroundColor: "rgba(0,123,255,0.3)",
        tension: 0.3,
        fill: true,
      },
    ],
  };

  const options = {
    scales: { y: { beginAtZero: true, max: 100 } },
  };

  {result && (
  <div className="results">
    <MetricCard metrics={result.metrics} recommendations={result.recommendations} />
  </div>
)}

{trendData.length > 0 && <SeoTrendChart trendData={trendData} />}

{predictedScore && (
  <div className="prediction-card">
    <h3>🔮 Predicted Next SEO Score</h3>
    <p>{predictedScore}/100 (based on previous trends)</p>
  </div>
)}


}
export default SeoTrendChart;
