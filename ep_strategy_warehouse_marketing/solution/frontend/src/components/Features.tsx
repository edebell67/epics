import React from 'react';

const Features: React.FC = () => {
  const pillars = [
    {
      id: 'capture',
      title: 'Signal Acquisition',
      description: 'Low-latency extraction from distributed warehouse adapters, unified into a single market thesis.',
      eyebrow: '01'
    },
    {
      id: 'frame',
      title: 'Evidence Framing',
      description: 'Automated assembly of performance metrics and trust signals to validate every distributed signal.',
      eyebrow: '02'
    },
    {
      id: 'convert',
      title: 'Conversion Flow',
      description: 'Streamlined subscription paths designed for high-conviction institutional and professional desks.',
      eyebrow: '03'
    }
  ];

  return (
    <section className="features-section" id="features">
      <div className="container">
        <div className="section-heading stage-enter">
          <span className="section-kicker">Core Infrastructure</span>
          <h2 className="section-title">Engineered for Clarity.</h2>
          <p className="section-subtitle">
            Our autonomous engine transforms raw warehouse data into professional-grade market intelligence.
          </p>
        </div>
        
        <div className="features-grid">
          {pillars.map((pillar) => (
            <article key={pillar.id} className="feature-card stage-enter">        
              <div className="feature-index">{pillar.eyebrow}</div>
              <h3 className="feature-title">{pillar.title}</h3>
              <p className="feature-description">{pillar.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Features;
