import React, { useState, useEffect } from 'react';
import { logConversionEvent, getUTMParams, getSessionId } from '../utils/tracking';

interface SubscriptionFormProps {
  sourceTag?: string;
}

interface SubscriptionErrorResponse {
  detail?: string;
}

// V20260321_1445 - C7: Integrated form conversion tracking and UTM attribution
const SubscriptionForm: React.FC<SubscriptionFormProps> = ({ sourceTag = 'landing_page' }) => {
  const [email, setEmail] = useState('');
  const [preferences, setPreferences] = useState({
    dailySignals: true,
    weeklyDigest: true,
    technicalAlerts: false,
  });
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // Log form_impression on component mount
  useEffect(() => {
    logConversionEvent('form_impression', {
      sourceTag,
      formId: 'subscription_main'
    });
  }, [sourceTag]);

  const validateEmail = (email: string) => {
    // Simple email validation to avoid quote issues in the script
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const handlePreferenceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setPreferences((prev) => ({ ...prev, [name]: checked }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setStatus('error');
      setErrorMessage('Email is required.');
      return;
    }

    if (!validateEmail(email)) {
      setStatus('error');
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setStatus('submitting');
    setErrorMessage('');

    try {
      // Capture tracking context for attribution
      const utm = getUTMParams();
      const sessionId = getSessionId();

      const response = await fetch('http://localhost:8000/subscriptions/', {    
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          preferences,
          source_tag: sourceTag,
          session_id: sessionId,
          ...utm
        }),
      });

      if (!response.ok) {
        const errorData: SubscriptionErrorResponse = await response.json();
        throw new Error(errorData.detail || 'Subscription failed. Please try again later.');
      }

      setStatus('success');
      setEmail('');
    } catch (err: unknown) {
      console.error('Subscription error:', err);
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'An unexpected error occurred.');
    }
  };

  if (status === 'success') {
    return (
      <div className='subscription-success'>
        <h3>Thank you for subscribing!</h3>
        <p>You’ll receive a confirmation email shortly. Please verify your email to start receiving signals.</p>
        <button className='secondary-button' onClick={() => setStatus('idle')}> 
          Back to site
        </button>
      </div>
    );
  }

  return (
    <div className='subscription-form-container'>
      <form onSubmit={handleSubmit} className='subscription-form'>
        <div className='form-group'>
          <input
            type='email'
            placeholder='Enter your email'
            className={`form-input ${status === 'error' ? 'input-error' : ''}`} 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={status === 'submitting'}
          />
          <button type='submit' className='primary-button' disabled={status === 'submitting'}>
            {status === 'submitting' ? 'Joining...' : 'Join List'}
          </button>
        </div>

        {status === 'error' && <p className='error-message'>{errorMessage}</p>} 

        <div className='preferences-group'>
          <p className='preferences-label'>Send me:</p>
          <div className='checkbox-items'>
            <label className='checkbox-item'>
              <input
                type='checkbox'
                name='dailySignals'
                checked={preferences.dailySignals}
                onChange={handlePreferenceChange}
                disabled={status === 'submitting'}
              />
              <span>Daily Signals</span>
            </label>
            <label className='checkbox-item'>
              <input
                type='checkbox'
                name='weeklyDigest'
                checked={preferences.weeklyDigest}
                onChange={handlePreferenceChange}
                disabled={status === 'submitting'}
              />
              <span>Weekly Digest</span>
            </label>
            <label className='checkbox-item'>
              <input
                type='checkbox'
                name='technicalAlerts'
                checked={preferences.technicalAlerts}
                onChange={handlePreferenceChange}
                disabled={status === 'submitting'}
              />
              <span>Tech Alerts</span>
            </label>
          </div>
        </div>
      </form>
    </div>
  );
};

export default SubscriptionForm;
