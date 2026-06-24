import React from "react";
import "./metriccard.css";

function MetricCard({ metrics, recommendations }) {
  const { seo_score, keyword_density, title_length, meta_description_length } = metrics;

  return (
    <div className="metric-card">
      <h2>📊 SEO Metrics</h2>

      <div className="progress">
        <div
          className="progress-bar"
          style={{
            width: `${seo_score}%`,
            background:
              seo_score > 70 ? "#4CAF50" : seo_score > 40 ? "#FFC107" : "#F44336",
          }}
        >
          {seo_score}%
        </div>
      </div>

      <p><b>Keyword Density:</b> {keyword_density}%</p>
      <p><b>Title Length:</b> {title_length} characters</p>
      <p><b>Meta Description Length:</b> {meta_description_length} characters</p>

      <h3>💡 Recommendations</h3>

      {recommendations.issues.length > 0 && (
        <ul className="issues">
          {recommendations.issues.map((i, index) => (
            <li key={index}>⚠️ {i}</li>
          ))}
        </ul>
      )}

      <h3>🤖 AI Suggestions</h3>
      <ul className="suggestions">
        {recommendations.suggestions.map((s, index) => (
          <li key={index}>✨ {s}</li>
        ))}
      </ul>
    </div>
  );
}

export default MetricCard;
