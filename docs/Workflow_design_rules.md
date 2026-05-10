👥 1. Actor → Agent Interaction Map
You only have 4 real actor types:

Guest (external customer)

Frontline Staff (front desk, housekeeping)

Management (manager, revenue team)

System/Admin (IT / dev / config)

🧑‍💬 2. Guest → interacts ONLY with Guest Agent
How:
Chat (web/app/WhatsApp)

Voice (optional later)

What they do:
Ask questions → G1

Book rooms → G1 → Booking Agent

Request services → G2 → Operations

Complain → G2 → Decision Agent (if needed)

Important:
Guest NEVER talks to Booking/Revenue/Operations directly

🧑‍💼 3. Frontline Staff → Operations + Decision Agent
A. Front Desk Staff
Interacts with:
Guest Agent (override mode)

Booking Agent

Decision Agent

How:
Internal dashboard / admin panel

What they do:
Override booking (manual changes)

Handle complex guest cases

Approve/reject AI decisions

B. Housekeeping / Ops Staff
Interacts with:
Operations Agent

How:
Mobile app / task dashboard

What they do:
Receive tasks (clean room, fix issue)

Update task status

Report problems

🧠 4. Management → Decision + Revenue Agent
A. Manager / Supervisor
Interacts with:
Decision Agent

How:
Dashboard / alerts

What they do:
Resolve escalations

Approve exceptions

Set policies (via rules layer)

B. Revenue / Sales Team
Interacts with:
Revenue Agent

How:
Analytics dashboard

What they do:
Override pricing

Set strategy (discounts, campaigns)

Monitor performance

⚙️ 5. System / Admin → Orchestrator + State Layer
Interacts with:
Orchestrator

State Layer

Rules system

How:
Admin tools / configs

What they do:
Configure system behavior

Debug issues

Maintain integrations

🔁 6. Conflict Resolution Flow (your key concern)
Example: Overbooking conflict
Booking Agent detects conflict

➡️ sends to Decision Agent

Decision Agent:

checks rules

evaluates options

If simple:
→ auto-resolve

If complex:
→ escalate to Manager (human)

Manager:
→ inputs decision

Decision Agent:
→ executes + updates state