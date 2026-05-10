# Workflow Test Cases

Comprehensive test suite for Hospitality AI Agents based on:
- `docs/Agent_setup_rules.md` - Agent dependencies and rules
- `docs/Workflow_design_rules.md` - Actor interaction patterns

## Test Categories

### 1. Guest Agent Tests (`TestGuestAgent`)
Tests G1 (Understand Intent), G2 (Respond), G3 (Personalize)

| Test | Description |
|------|-------------|
| `test_g1_understand_booking_intent` | Detects booking-related intents |
| `test_g1_understand_service_intent` | Detects service request intents |
| `test_g2_respond_to_general_inquiry` | Responds to general questions |
| `test_g3_personalize_based_on_profile` | Uses guest profile for personalization |
| `test_guest_never_talks_to_booking_directly` | Enforces routing through orchestrator |
| `test_conversation_memory` | Maintains conversation context |

### 2. Booking Flow Tests (`TestBookingFlow`)
Tests B1 (Availability), B2 (Reservation), B3 (Pricing)

| Test | Description |
|------|-------------|
| `test_b1_availability_check` | Checks room availability |
| `test_b2_create_reservation` | Creates confirmed bookings |
| `test_b3_pricing_with_revenue_dependency` | Gets pricing from Revenue Agent |
| `test_booking_triggers_operations` | Triggers room prep tasks |
| `test_overbooking_conflict_resolution` | Escalates overbooking to Decision Agent |

### 3. Operations Agent Tests (`TestOperationsAgent`)
Tests O1 (Task Assignment), O2 (Scheduling), O3 (Execution Tracking)

| Test | Description |
|------|-------------|
| `test_o1_task_assignment` | Assigns tasks to staff |
| `test_o2_scheduling` | Schedules urgent tasks immediately |
| `test_o3_execution_tracking` | Tracks task completion status |
| `test_operations_reports_conflicts` | Reports resource conflicts |

### 4. Decision Agent Tests (`TestDecisionAgent`)
Tests D1 (Edge Cases), D2 (Policy Enforcement), D3 (Human Escalation)

| Test | Description |
|------|-------------|
| `test_d1_edge_case_handling` | Handles unusual requests |
| `test_d2_policy_enforcement` | Enforces hotel policies |
| `test_d3_human_escalation` | Escalates to human managers |

### 5. Revenue Agent Tests (`TestRevenueAgent`)
Tests R1 (Pricing), R2 (Demand Prediction), R3 (Strategy)

| Test | Description |
|------|-------------|
| `test_r1_pricing_optimization` | Optimizes room pricing |
| `test_r2_demand_prediction` | Forecasts demand patterns |
| `test_r3_strategy_recommendations` | Provides revenue strategies |

### 6. Orchestrator Tests (`TestOrchestrator`)
Tests routing and coordination

| Test | Description |
|------|-------------|
| `test_route_to_correct_agent` | Routes problems to correct agent |
| `test_execution_order` | Ensures correct execution sequence |
| `test_prevent_conflicts` | Prevents concurrent modification conflicts |

### 7. Dependency Rule Tests (`TestDependencyRules`)
Tests Agent_setup_rules.md rules

| Test | Rule | Description |
|------|------|-------------|
| `test_rule1_no_random_agent_calls` | Rule 1 | No random agent communication |
| `test_rule2_single_owner` | Rule 2 | One owner per problem |
| `test_rule3_decision_agent_not_default` | Rule 3 | Decision Agent not default |
| `test_decision_agent_only_for_conflicts` | - | Only for conflicts/ambiguity |

### 8. Actor Interaction Tests (`TestActorInteractions`)
Tests Workflow_design_rules.md actor flows

| Test | Actor | Description |
|------|-------|-------------|
| `test_guest_only_talks_to_guest_agent` | Guest | Guest → Guest Agent only |
| `test_frontline_staff_interactions` | Frontline | Staff → Operations + Decision |
| `test_management_interactions` | Management | Manager → Decision + Revenue |
| `test_system_admin_interactions` | Admin | Admin → Orchestrator + State |

### 9. Integration Tests (`TestWorkflowIntegration`)
End-to-end workflows

| Test | Workflow | Steps |
|------|----------|-------|
| `test_complete_booking_workflow` | Full booking | Guest → Orchestrator → Booking → Revenue → Booking → Operations → Guest |
| `test_complaint_escalation_workflow` | Complaint | Guest → Orchestrator → Decision → Manager |

## Running Tests

```bash
# Run all tests
pytest tests/test_workflow.py -v

# Run specific test class
pytest tests/test_workflow.py::TestGuestAgent -v

# Run specific test
pytest tests/test_workflow.py::TestGuestAgent::test_g1_understand_booking_intent -v

# Run with debug output
pytest tests/test_workflow.py -v --log-cli-level=DEBUG
```

## Test Coverage

- **Guest Agent**: Intent detection, personalization, memory, routing
- **Booking Agent**: Availability, pricing, reservations, conflict handling
- **Operations Agent**: Task assignment, scheduling, tracking
- **Decision Agent**: Edge cases, policies, human escalation
- **Revenue Agent**: Pricing, demand forecasting, strategy
- **Orchestrator**: Routing, execution order, conflict prevention
- **Dependencies**: All 3 rules enforced
- **Actor Flows**: All 4 actor types
- **Integration**: Complete workflows

## AI-Simulated Tests (`test_workflow_ai_simulated.py`)

Automated conversational testing using an LLM to simulate human guests.
**No human input required!**

### How It Works
1. **AI Guest Simulator** (`test_helpers/ai_guest_simulator.py`) creates a persona
2. LLM plays the role of the guest based on persona traits
3. Simulator converses with your actual Guest Agent
4. Tests verify the agent handles the conversation correctly

### Predefined Guest Personas

| Persona | Guest | Goal | Traits |
|---------|-------|------|--------|
| `business_booking` | Business Bob | Book room for 2 nights, quiet for meetings | impatient, direct |
| `family_vacation` | Family Fiona | Book for family of 4, 5 nights with breakfast | detail_oriented, friendly |
| `complainer` | Complaining Carl | Complain about dirty room, demand manager | frustrated, demanding |
| `price_shopper` | Price Patty | Find cheapest room for weekend | price_conscious, comparative |
| `service_requester` | Service Sam | Request towels, room service, late checkout | polite, specific |
| `confused_guest` | Confused Clara | Needs guidance on amenities | uncertain, questioning |

### AI Simulated Tests

| Test | AI Guest | What It Tests |
|------|----------|---------------|
| `test_guest_agent_handles_business_booking` | Business Bob | Booking intent detection and routing |
| `test_guest_agent_handles_family_booking` | Family Fiona | Complex booking with details |
| `test_guest_agent_handles_complaint` | Complaining Carl | Complaint handling and escalation |
| `test_guest_agent_handles_pricing_questions` | Price Patty | Pricing query routing |
| `test_guest_agent_handles_service_requests` | Service Sam | Service request routing |
| `test_guest_agent_handles_confused_guest` | Confused Clara | Helpful guidance |
| `test_conversation_memory_across_turns` | Memory Mike | Context retention |
| `test_complete_booking_journey` | Journey Jane | Full end-to-end booking |
| `test_multi_intent_conversation` | Multi Mike | Handling shifting intents |
| `test_pricing_query_routes_to_orchestrator` | Price Paula | **CRITICAL: Pricing routing fix** |

### Running AI Simulated Tests

```bash
# Run all AI simulated tests
pytest tests/test_workflow_ai_simulated.py -v

# Run specific AI test
pytest tests/test_workflow_ai_simulated.py::TestGuestAgentWithAISimulation::test_pricing_query_routes_to_orchestrator -v

# Run with full conversation output
pytest tests/test_workflow_ai_simulated.py -v -s
```

### Quick Test Helper

```python
from tests.test_helpers.ai_guest_simulator import test_with_simulated_guest

def my_agent_api(guest_id, message):
    # Your agent API call
    return response

# Test with one line
result = test_with_simulated_guest("business_booking", my_agent_api, verbose=True)
assert result["goal_achieved"] is True
```

## Expected Agent Behaviors

### Guest Agent
- Detects: booking intent, service requests, general questions, complaints
- Routes: booking/pricing → Orchestrator, service → Operations, complaint → Decision
- Never answers pricing directly (always routes)
- Maintains conversation history (last 10 messages)
- Personalizes using guest profile

### Booking Agent
- Checks availability (B1)
- Gets pricing from Revenue Agent (B3 dependency)
- Creates reservations (B2)
- Triggers Operations for room prep
- Escalates conflicts to Decision Agent

### Operations Agent
- Assigns tasks to staff (O1)
- Schedules urgent tasks first (O2)
- Tracks completion (O3)
- Reports resource conflicts to Decision Agent

### Decision Agent
- Handles edge cases (D1)
- Enforces policies (D2)
- Escalates to humans when needed (D3)
- NOT default - only for conflicts/ambiguity

### Revenue Agent
- Optimizes pricing (R1)
- Predicts demand (R2)
- Recommends strategies (R3)
- Does NOT talk to guests directly

### Orchestrator
- Routes to correct agent
- Ensures execution order
- Prevents conflicts with resource locking
- All agents go through Orchestrator for coordination
