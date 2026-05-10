Actor → Interface (UI) → Actions → Which Agent → Input/Output

🧑‍💬 1. GUEST INTERFACE (Chat-first system)
🎯 Interface: Guest Chat (web/app/WhatsApp)
What guest can do:
1. Ask / inquire
“Do you have rooms tomorrow?”
→ Guest Agent (G1)
→ Output: answer (availability summary)

2. Book a room
“Book 2 nights for me”
→ Guest Agent → Booking Agent
→ Output: confirmation message

3. Request service
“I need extra towels”
→ Guest Agent → Operations Agent
→ Output: “Task created, coming soon”

4. Complain / issue
“Room is dirty”
→ Guest Agent → Decision Agent (if serious)
→ Output: apology + resolution

🧠 API shape (simplified)
POST /guest/message
{
  "guest_id": "G123",
  "message": "I want to book a room tomorrow"
}
Response:

{
  "reply": "We have rooms available. Would you like to proceed?",
  "action": "booking_intent_detected"
}
🧑‍💼 2. FRONT DESK DASHBOARD
🎯 Interface: Staff Dashboard (web panel)
What staff can do:
1. Override booking
→ Booking Agent

POST /booking/override
{
  "reservation_id": "R001",
  "action": "modify",
  "new_dates": "..."
}
2. Handle complex guest
→ Decision Agent

POST /decision/manual
{
  "case_id": "C123",
  "decision": "approve_upgrade"
}
3. View guest state
→ State Layer (read)

🧹 3. OPERATIONS APP (Housekeeping / Staff)
🎯 Interface: Task Mobile App
What they do:
1. Receive tasks
← Operations Agent

GET /tasks?staff_id=H001
2. Update task status
POST /tasks/update
{
  "task_id": "T001",
  "status": "completed"
}
→ updates State
→ triggers next workflow

3. Report issue
POST /tasks/issue
{
  "task_id": "T001",
  "issue": "AC not working"
}
→ Operations → Decision Agent

🧠 4. MANAGEMENT DASHBOARD
🎯 Interface: Decision + Monitoring Panel
What manager does:
1. Resolve escalations
→ Decision Agent

POST /decision/escalation
{
  "case_id": "C999",
  "action": "refund"
}
2. Set policies (via rules)
POST /rules/update
{
  "rule": "no_overbooking"
}
3. Monitor system
GET /analytics/performance
💰 5. REVENUE DASHBOARD
🎯 Interface: Pricing Control Panel
What they do:
1. Override pricing
POST /pricing/update
{
  "room_type": "deluxe",
  "price": 120
}
→ Revenue Agent updates State

2. Set strategy
POST /pricing/strategy
{
  "rule": "increase_price_if_occupancy_above_80%"
}
⚙️ 6. ADMIN / SYSTEM PANEL
🎯 Interface: System Control
What they do:
Configure orchestrator flows

Debug logs

Manage integrations

🔁 7. FULL FLOW (UI → Agent → UI)
Booking example:
Guest Chat:
→ /guest/message

Guest Agent:
→ detect intent

Orchestrator:
→ route to Booking Agent

Booking Agent:
→ check State
→ ask Revenue Agent

State updated

Guest Agent:
→ reply via chat UI