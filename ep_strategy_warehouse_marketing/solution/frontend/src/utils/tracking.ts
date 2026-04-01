// V20260321_1445 - C7: Client-side tracking utility for conversion events and UTM capture

export interface UTMPars {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content?: string;
  utm_term?: string;
}

type ConversionMetadata = Record<string, string | number | boolean | null | undefined>;

export const getUTMParams = (): UTMPars => {
  const urlParams = new URLSearchParams(window.location.search);
  return {
    utm_source: urlParams.get('utm_source') || undefined,
    utm_medium: urlParams.get('utm_medium') || undefined,
    utm_campaign: urlParams.get('utm_campaign') || undefined,
    utm_content: urlParams.get('utm_content') || undefined,
    utm_term: urlParams.get('utm_term') || undefined,
  };
};

export const getSessionId = (): string => {
  let sessionId = localStorage.getItem('sw_session_id');
  if (!sessionId) {
    sessionId = 'sess_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('sw_session_id', sessionId);
  }
  return sessionId;
};

export const logConversionEvent = async (
  eventType: string, 
  metadata: ConversionMetadata = {}
) => {
  const utm = getUTMParams();
  const sessionId = getSessionId();
  
  try {
    await fetch('http://localhost:8000/conversions/log', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        event_type: eventType,
        session_id: sessionId,
        url: window.location.href,
        ...utm,
        event_metadata: metadata
      }),
    });
  } catch (error) {
    console.warn('Conversion logging failed:', error);
  }
};
