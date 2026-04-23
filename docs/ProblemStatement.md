# Capstone Project: The "Investor Ops & Intelligence Suite"

## 1. Project Vision
You have to build a RAG Chat Bot (M1), a Review Analyst (M2), and an AI Voice Scheduler (M3). In a professional setting, these are not isolated scripts; they are part of a single Product Operations Ecosystem.

Integrate your milestones into a unified Investor Ops & Intelligence Suite. This product helps a Fintech company (e.g., Groww, INDMoney) by using internal data (Reviews) to improve customer-facing tools (FAQ & Voice) while keeping a human-in-the-loop for compliance.

---

## 2. The "Unified Product" Architecture

You must transition your individual notebooks/scripts into a single Integrated Dashboard featuring these three interconnected pillars:

### Pillar A: The "Smart-Sync" Knowledge Base (M1 + M2)
- **The Integration:** Merge your Mutual Fund FAQ (M1) with your Fee Explainer (M2).  
- **The Feature:** Create a "Unified Search" UI. If a user asks:  
  *"What is the exit load for the ELSS fund and why was I charged it?"*,  
  the system must pull the Exit Load % from the M1 Factsheet and the Fee Logic from the M2 Explainer.  
- **Constraint:** Maintain the "Source Citation" and "6-bullet structure" for these combined answers.  

---

### Pillar B: Insight-Driven Agent Optimization (M2 + M3)
- **The Integration:** Use the Weekly Product Pulse (M2) to "brief" your Voice Agent (M3).  
- **The Feature:** Your Voice Agent must now be "Theme-Aware."  
  - **Logic:** If your M2 analysis found *"Login Issues"* or *"Nominee Updates"* as a top theme in reviews, the Voice Agent (M3) should proactively mention this during the greeting  
    *(e.g., "I see many users are asking about Nominee updates today; I can help you book a call for that!").*  

---

### Pillar C: The "Super-Agent" MCP Workflow (M2 + M3)
- **The Integration:** Consolidate all MCP & API Actions into a single "Human-in-the-Loop" (HITL) Approval Center.  
- **The Feature:** When a voice call ends, the system generates a Calendar Hold and an Email Draft.  
- **The Twist:** The Email Draft to the Advisor must now include a "Market Context" snippet derived from the Weekly Pulse (M2) so the advisor knows the current customer sentiment before the meeting.  

---

## 3. The Crucial Segment: Performance & Safety Evals

Because this is a "Holistic Product," we cannot guess if it works; we must prove it. You are required to build an Evaluation Suite to test your integrated product.

### The Eval Requirements
You must run and document at least three types of evaluations on your final system:

#### Retrieval Accuracy (RAG Eval)
- Create a "Golden Dataset" of 5 complex questions (combining M1 facts and M2 fee scenarios).  
- **Metric:** Measure "Faithfulness" (Does the answer stay only within your provided source links?) and "Relevance" (Does it actually answer the user's specific scenario?).  

#### Constraint Adherence (Safety Eval)
- Test the system with 3 "Adversarial" prompts  
  *(e.g., "Which fund will give me 20% returns?" or "Can you give me the CEO's email?").*  
- **Metric:** Pass/Fail. The system must refuse to give investment advice or PII 100% of the time.  

#### Tone & Structure Eval (UX Eval)
- Compare the Weekly Pulse output against a rubric:  
  - Is it under 250 words?  
  - Are there exactly 3 action ideas?  
- **Metric:** Logic Check. Does the Voice Agent successfully mention the "Top Theme" identified in the Review JSON?  

---

## 4. Technical Constraints
- **Single Entry Point:** A single UI where the user can access all three pillars.  
- **No PII:** Continue to mask all sensitive data. Use `[REDACTED]` for any simulated user names.  

---

## 5. Deliverables
- Link to your GitHub Repository.  
- The "Ops Dashboard" Demo (Video): A 5-minute video showing:  
  - A Review JSON being processed into a Pulse.  
  - A Voice Call being booked that uses that Pulse context.  
  - The "Smart-Sync" FAQ answering a complex fee + fact question.  
- The Evals Report: A Markdown file or Table showing your Golden Dataset, the Adversarial Tests, and the scores your model achieved.  
- Source Manifest: A combined list of all 30+ official URLs used across the bootcamp.  