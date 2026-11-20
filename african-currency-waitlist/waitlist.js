const form = document.querySelector('#waitlistForm');
const status = document.querySelector('#formStatus');
form.addEventListener('submit', async event => {
 event.preventDefault(); if (!form.reportValidity()) return;
 const button = form.querySelector('button'); button.disabled = true; status.textContent = 'Sending…';
 const data = Object.fromEntries(new FormData(form)); data.consent = form.elements.consent.checked;
 const params = new URLSearchParams(location.search); for (const key of ['utm_source','utm_medium','utm_campaign','utm_content']) data[key] = params.get(key) || '';
 data.referrer = document.referrer; data.landingPath = location.pathname;
 try { const response = await fetch('https://african-currency-waitlist.edbell.chatgpt.site/api/waitlist', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); if (!response.ok) throw new Error('Registration failed'); form.reset(); status.textContent = 'You’re on the list. Thank you for joining the conversation.'; }
 catch { status.textContent = 'Registration is currently unavailable. Please try again later.'; }
 finally { button.disabled = false; }
});
