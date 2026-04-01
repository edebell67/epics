import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="footer-section">
      <div className="container">
        <div className="footer-container">
          <div className="footer-brand">
            <h4 className="footer-brand-title">Strategy Warehouse</h4>
            <p className="text-muted">
              Professional-grade signal distribution and performance audit engine.
            </p>
          </div>
          
          <div className="footer-links">
            <div className="footer-column">
              <h5>Navigation</h5>
              <ul>
                <li><a href="#top">Hero</a></li>
                <li><a href="#features">Infrastructure</a></li>
                <li><a href="#proof">Evidence</a></li>
              </ul>
            </div>
            <div className="footer-column">
              <h5>Command</h5>
              <ul>
                <li><a href="/dashboard">Dashboard</a></li>
                <li><a href="#join">Subscribe</a></li>
                <li><a href="#proof">Proof Audit</a></li>
              </ul>
            </div>
          </div>
        </div>
        
        <div className="footer-bottom">
          <p className="text-muted">
            &copy; 2026 Strategy Warehouse. Performance data refreshed every 17 minutes.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
