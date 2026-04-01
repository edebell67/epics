import React from 'react';
import heroImage from '../assets/hero.png';

const Hero: React.FC = () => {
  return (
    <section className="hero-section" id="top">
      <div className="hero-backdrop" aria-hidden="true">
        <div className="hero-glow hero-glow-1" />
        <div className="hero-glow hero-glow-2" />
      </div>

      <div className="container hero-container">
        <div className="hero-content stage-enter stage-enter-delay-1">
          <header className="hero-header">
            <span className="hero-eyebrow">Strategy Warehouse</span>
            <span className="hero-badge">v2026.03.22</span>
          </header>

          <h1 className="hero-headline">
            Market Intelligence <br />
            <span className="text-accent">Redefined.</span>
          </h1>

          <p className="hero-subheadline">
            Autonomous signal distribution engineered for professional operators. 
            Turn warehouse output into sharp, actionable briefings with integrated proof.
          </p>

          <div className="hero-actions">
            <button 
              className="btn btn-primary" 
              onClick={() => window.location.href = '/dashboard'}
            >
              Enter Command Layer
            </button>
            <a href="#proof" className="btn btn-secondary">
              Inspect Evidence
            </a>
          </div>

          <footer className="hero-footer-meta">
            <div className="hero-meta-item">
              <span className="meta-label">Signal Cadence</span>
              <span className="meta-value">17 Min Refresh</span>
            </div>
            <div className="hero-meta-item">
              <span className="meta-label">Active Lanes</span>
              <span className="meta-value">24 Concurrent</span>
            </div>
          </footer>
        </div>

        <div className="hero-visual-wrapper stage-enter stage-enter-delay-2">
          <div className="hero-visual-frame">
            <img 
              src={heroImage} 
              alt="Strategy Warehouse Interface" 
              className="hero-main-image"
            />
            <div className="hero-visual-overlay">
              <div className="overlay-line" />
              <div className="overlay-pulse" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
