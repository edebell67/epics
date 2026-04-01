import React, { useEffect, useState } from 'react';
import { loadSocialProofViewModel, type SocialProofViewModel } from './socialProofData';

const SocialProof: React.FC = () => {
  const [viewModel, setViewModel] = useState<SocialProofViewModel | null>(null);

  useEffect(() => {
    let active = true;

    void loadSocialProofViewModel().then((data) => {
      if (active) {
        setViewModel(data);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  if (!viewModel) {
    return (
      <section className="social-proof-section" id="proof">
        <div className="container">
          <span className="section-kicker">Proof Pipeline</span>
          <h2 className="section-title">Loading Evidence...</h2>
        </div>
      </section>
    );
  }

  return (
    <section className="social-proof-section" id="proof">
      <div className="container">
        <div className="social-proof-shell">
          <header className="social-proof-intro">
            <span className="section-kicker">Validation Layer</span>
            <div className="proof-heading-row">
              <h2 className="section-title">Verified Performance.</h2>
              <span className={`proof-source-badge ${viewModel.source}`}>{viewModel.sourceLabel}</span>
            </div>
            <p className="section-subtitle">
              Atmosphere turns into evidence. Source health, trust signals, and audited market briefings.
            </p>
          </header>

          <div className="proof-metrics-grid">
            {viewModel.proofMetrics.map((metric) => (
              <article key={metric.id} className="proof-metric-card">
                <span className="meta-label">{metric.label}</span>
                <strong className="proof-metric-value">{metric.value}</strong>
                <p className="text-muted">{metric.detail}</p>
              </article>
            ))}
          </div>

          <div className="proof-detail-grid">
            <div className="trust-signals-panel">
              <div className="trust-signals-header">
                <h3 className="proof-panel-title">Trust Signals</h3>
                <span className="proof-generated-at">Refreshed {viewModel.generatedAt}</span>
              </div>
              <div className="trust-signals-list">
                {viewModel.trustSignals.map((signal) => (
                  <article key={signal.id} className="trust-signal-card">
                    <h4 className="trust-signal-title">{signal.title}</h4>
                    <p className="trust-signal-detail">{signal.detail}</p>
                  </article>
                ))}
              </div>
            </div>

            <div className="social-proof-grid">
              {viewModel.posts.map((post) => (
                <article key={post.id} className="social-post">
                  <div className="post-header">
                    <span className="platform-tag">{post.platform}</span>
                    <span className="post-pillar">{post.pillar}</span>
                  </div>
                  <div className="post-content">
                    <h4 className="post-headline">{post.headline}</h4>
                    <p className="post-body">{post.body}</p>
                  </div>
                  <div className="post-footer">
                    <span className="live-badge">{viewModel.source === 'live' ? 'LIVE' : 'SIM'}</span>
                    <span className="post-timestamp">{post.publishedLabel}</span>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SocialProof;
