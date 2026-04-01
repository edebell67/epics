import React from 'react';
import SubscriptionForm from './SubscriptionForm';

const CTA: React.FC = () => {
  return (
    <section className="cta-section" id="join">
      <div className="container">
        <div className="cta-container">
          <div className="cta-copy">
            <span className="section-kicker">Join the Network</span>
            <h2 className="cta-title">Subscribe to the Signal Desk.</h2>
            <p className="cta-subtitle">
              Receive the next intelligence batch directly from the Strategy Warehouse command layer.
            </p>
            <div className="cta-note-list" aria-hidden="true">
              <span>Institutional Grade</span>
              <span>17m Freshness</span>
              <span>Full Proof Audit</span>
            </div>
          </div>
          <div className="cta-form-shell">
            <SubscriptionForm sourceTag="cta_footer" />
          </div>
        </div>
      </div>
    </section>
  );
};

export default CTA;
