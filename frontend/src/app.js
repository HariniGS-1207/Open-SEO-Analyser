// App.js
import React, { useState } from "react";
import "./app.css";
import MetricCard from "./components/metriccard";
import Loader from "./components/loader";

function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [optimized, setOptimized] = useState(null);

  // ---------------------------
  // Analyze SEO
  // ---------------------------
  const handleAnalyze = async () => {
    if (!url.trim()) {
      setError("⚠️ Please enter a website URL.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setOptimized(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        throw new Error("Failed to analyze");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("❌ Unable to analyze website. Please check your backend or try again.");
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------
  // AI Optimization
  // ---------------------------
  const handleOptimize = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/auto_optimize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      const data = await response.json();
      setOptimized(data);
    } catch (err) {
      setError("❌ Optimization failed. Please try again.");
    }
  };

  return (
    <div className="app">
      {/* Background Animation */}
      <div className="bg-circle one"></div>
      <div className="bg-circle two"></div>

      <header className="hero">
        <div className="hero-copy">
          <span className="eyebrow">SEO + AI for smarter websites</span>
          <h1>Open SEO & AI Optimizer</h1>
          <p>
            Fast, friendly website analysis with actionable SEO insights and AI-driven
            optimization recommendations for better search visibility.
          </p>
        </div>

        <div className="search-box">
          <input
            type="text"
            placeholder="Enter website URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button onClick={handleAnalyze} disabled={loading}>
            {loading ? "Analyzing..." : "Analyze Website"}
          </button>
        </div>

        {error && <div className="error-box">{error}</div>}
      </header>

      <section className="feature-grid">
        <div className="feature-card">
          <h3>Instant SEO Health</h3>
          <p>Scan your website fast and see the strongest opportunities for improvement.</p>
        </div>
        <div className="feature-card">
          <h3>AI-Powered Suggestions</h3>
          <p>Receive practical optimization ideas for titles, meta tags, content, and keywords.</p>
        </div>
        <div className="feature-card">
          <h3>Data-Driven Results</h3>
          <p>Compare before/after scores and understand exactly how your SEO improves.</p>
        </div>
      </section>

      {loading && <Loader />}

      {result && (
        <section className="dashboard">
          <div className="result-summary">
            <div className="score-card">
              <h2>SEO Score</h2>
              <div className="score-circle">{result.metrics.seo_score}</div>
              <p>
                {result.metrics.seo_score >= 80
                  ? "Excellent SEO performance 🎯"
                  : result.metrics.seo_score >= 60
                  ? "Solid SEO — your site can still improve ⚡"
                  : "SEO needs attention — start optimizing now 🚨"}
              </p>
            </div>

            <MetricCard
              metrics={result.metrics}
              recommendations={result.recommendations}
            />
          </div>

          <div className="ai-card">
            <h2>🤖 AI Suggestions</h2>
            <ul>
              {result.recommendations.suggestions.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
            <button className="optimize-btn" onClick={handleOptimize}>
              ⚡ Apply AI Optimization
            </button>
          </div>
        </section>
      )}

      {optimized && (
        <section className="optimized-box">
          <h2>✨ Optimization Summary</h2>
          <div className="comparison">
            <div className="compare-card">
              <h3>Before</h3>
              <p>{result.metrics.seo_score}/100</p>
            </div>
            <div className="compare-card after-card">
              <h3>After</h3>
              <p>{optimized.after_score}/100</p>
            </div>
          </div>
          <div className="meta-section">
            <div>
              <h3>Old Title</h3>
              <p>{optimized.old_title}</p>
            </div>
            <div>
              <h3>New Title</h3>
              <p>{optimized.new_title}</p>
            </div>
            <div>
              <h3>Old Meta</h3>
              <p>{optimized.old_meta}</p>
            </div>
            <div>
              <h3>New Meta</h3>
              <p>{optimized.new_meta}</p>
            </div>
          </div>
        </section>
      )}

      <section className="about-section">
        <div className="about-content">
          <h2>About Open SEO & AI Optimizer</h2>
          <p>
            Open SEO & AI Optimizer helps website owners, marketers, and small businesses
            understand their SEO performance quickly. This tool analyzes key on-page signals
            and delivers easy-to-follow recommendations.
          </p>
          <p>
            Our mission is to make SEO simple and actionable. Check title tags, meta descriptions,
            keyword use, and content health—all in one clean interface.
          </p>
          <div className="about-grid">
            <div className="about-card">
              <h3>Who it helps</h3>
              <p>Anyone who wants better search visibility and clearer optimization guidance.</p>
            </div>
            <div className="about-card">
              <h3>What it does</h3>
              <p>Analyzes your page, highlights SEO opportunities, and suggests AI-powered improvements.</p>
            </div>
            <div className="about-card">
              <h3>Why it matters</h3>
              <p>Better SEO means more traffic, stronger rankings, and stronger online credibility.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default App;