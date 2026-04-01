import React, { useEffect } from 'react';
import Hero from '../components/Hero';
import Features from '../components/Features';
import SocialProof from '../components/SocialProof';
import CTA from '../components/CTA';
import Footer from '../components/Footer';
import { logConversionEvent } from '../utils/tracking';

// V20260321_1445 - C7: Integrated page_view conversion tracking on load
const LandingPage: React.FC = () => {
  useEffect(() => {
    logConversionEvent('page_view', {
      title: document.title,
      referrer: document.referrer
    });
  }, []);

  return (
    <div className="landing-page-container">
      <Hero />
      <Features />
      <SocialProof />
      <CTA />
      <Footer />
    </div>
  );
};

export default LandingPage;
