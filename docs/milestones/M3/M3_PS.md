# AI Appointment Scheduler

Voice Agent: Advisor Appointment Scheduler is a compliant, pre booking voice assistant that helps users quickly secure a tentative slot with a human advisor. It collects the consultation topic and preferred time, offers available slots, confirms the booking, and generates a unique booking code. The agent then creates a calendar hold, updates internal sheets via API and drafts an approval gated email using MCP. No personal data is taken on the call, clear disclaimers are enforced. This milestone tests practical voice UX, safe intent handling, and real world AI system orchestration rather than just conversation quality.

---

## Voice Agent: Advisor Appointment Scheduler

### Milestone brief
Create a voice agent that books a tentative advisor slot: collects topic + time preference, offers two slots, confirms, and then creates a calendar hold and sheets entry via API + email draft via MCP. The caller gets a booking code.

---

## Who this helps
Users who want a human consult; PMs/Support running compliant pre-booking.

---

## What you must build

### Intents (3):
- book new  
- reschedule  
- cancel   

---

### Flow:
greet(while mentioning the top 3 themes from M2) → disclaimer (“informational, not investment advice”) → confirm topic (Top 3 themes from M2) → collect day/time preference → offer two slots → on confirm:

- Generate Booking Code (e.g., NL-A742).  

- API Calendar: create tentative hold “Advisor Q&A — {Topic} — {Code}”.  

- API Google Sheets: append {date, topic, slot, code} to “Advisor Pre-Bookings”.  

- MCP Email Draft: prepare advisor email with details (approval-gated).  

- Read the booking code.  

---

## Key constraints
- No PII on the call (no phone/email/account numbers).  
- State time zone (IST) and repeat date/time on confirm.  
- Refuse investment advice; provide educational links if asked.  
