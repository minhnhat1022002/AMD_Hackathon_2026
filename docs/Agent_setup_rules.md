the IMPORTANT part: Dependencies (who talks to who)
This is where systems usually break—so we make it explicit.

🧑‍💬 Guest Agent
Solves:
G1: Understand intent

G2: Respond

G3: Personalize

Needs:
➡️ Booking Agent (when booking intent detected)

➡️ Decision Agent (when confused / ambiguous / complaint)

➡️ State Layer (guest profile)

📅 Booking Agent
Solves:
B1: Availability

B2: Reservation

B3: Pricing application

Needs:
➡️ Revenue Agent (for pricing)

➡️ Operations Agent (trigger room prep)

➡️ Decision Agent (conflicts: overbooking, special cases)

➡️ State Layer

🏨 Operations Agent
Solves:
O1: Task assignment

O2: Scheduling

O3: Execution tracking

Needs:
➡️ Booking Agent (new reservations)

➡️ Decision Agent (resource conflicts, failures)

➡️ State Layer

🧠 Decision Agent
Solves:
D1: Edge cases

D2: Policy enforcement

D3: Human escalation

Needs:
➡️ ALL agents (it’s the fallback brain)

➡️ Rules / Knowledge Base

➡️ Humans (staff input)

💰 Revenue Agent
Solves:
R1: Pricing optimization

R2: Demand prediction

R3: Strategy

Needs:
➡️ State Layer (occupancy, bookings)

➡️ (optional) external market data

❗ Does NOT talk to guests directly

🎯 Orchestrator (critical control)
Solves:
Routing problems to correct agent

Ensuring order of execution

Preventing conflicts

Needs:
➡️ ALL agents

➡️ State Layer

🔄 Example dependency flow (very concrete)
Problem: “Guest wants to book a room”
Guest Agent → solves G1

detects booking intent

➡️ sends to Booking Agent

Booking Agent → solves B1 + B3

checks availability

➡️ asks Revenue Agent for price

Revenue Agent → solves R1

returns price

Booking Agent → solves B2

creates reservation

➡️ notifies Operations Agent

Operations Agent → solves O1

creates cleaning task

Guest Agent → solves G2

sends confirmation

Rules you MUST enforce
Rule 1:
Agents do NOT randomly call each other

Only allowed if:

needed to solve a problem

or routed via Orchestrator

Rule 2:
Every problem must have ONE owner agent

No shared responsibility
→ avoids chaos

Rule 3:
Decision Agent is NOT default

Only used when:

conflict

ambiguity

exception