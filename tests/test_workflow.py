"""
Workflow Test Cases for Hospitality AI Agents

Based on:
- docs/Agent_setup_rules.md - Agent dependencies and rules
- docs/Workflow_design_rules.md - Actor interaction patterns

Test Categories:
1. Guest Agent Tests (G1-G3)
2. Booking Flow Tests (B1-B3)
3. Operations Tests (O1-O3)
4. Decision Agent Tests (D1-D3)
5. Revenue Agent Tests (R1-R3)
6. Orchestrator Tests
7. Dependency Rule Tests
8. Actor Interaction Tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

# Import all agents
from hospitality_ai.agents.guest_agent import guest_agent, GuestMessage, GuestResponse
from hospitality_ai.agents.booking_agent import booking_agent, BookingRequest, BookingResponse
from hospitality_ai.agents.operations_agent import operations_agent, ServiceRequest, TaskResponse
from hospitality_ai.agents.decision_agent import decision_agent, EscalationRequest, DecisionResponse
from hospitality_ai.agents.revenue_agent import revenue_agent, PricingRequest, RevenueResponse
from hospitality_ai.agents.orchestrator import orchestrator, WorkflowRequest, WorkflowResponse

# Import state layer
from hospitality_ai.domain.state_layer import state_layer, GuestProfile, RoomStatus, BookingStatus


class TestGuestAgent:
    """Test Guest Agent (G1, G2, G3) - Guest interaction and intent understanding"""

    def test_g1_understand_booking_intent(self):
        """G1: Guest Agent must detect booking intent"""
        messages = [
            "I want to book a room",
            "Do you have rooms available?",
            "Can I make a reservation for May 18th?",
            "Looking for a room with two beds",
            "What are your rates?"
        ]

        for msg in messages:
            request = GuestMessage(guest_id="G123", message=msg)
            response = guest_agent.process_message(request)

            assert response.action in [
                "routed_to_orchestrator",
                "booking_intent_detected",
                "checked_availability"
            ], f"Should detect booking intent for: {msg}"

    def test_g1_understand_service_intent(self):
        """G1: Guest Agent must detect service request intent"""
        messages = [
            "I need housekeeping",
            "Can I get room service?",
            "The AC is not working",
            "I need more towels"
        ]

        for msg in messages:
            request = GuestMessage(guest_id="G123", message=msg)
            response = guest_agent.process_message(request)

            assert response.action in [
                "routed_to_orchestrator",
                "service_request_detected"
            ], f"Should detect service intent for: {msg}"

    def test_g2_respond_to_general_inquiry(self):
        """G2: Guest Agent must respond to general questions without tools"""
        request = GuestMessage(guest_id="G123", message="What time is breakfast?")
        response = guest_agent.process_message(request)

        assert response.action == "responded"
        assert response.message  # Should have actual response text
        assert len(response.message) > 10  # Substantive response

    def test_g3_personalize_based_on_profile(self):
        """G3: Guest Agent must use guest profile for personalization"""
        # Setup guest profile
        profile = GuestProfile(
            guest_id="G123",
            name="John Doe",
            preferences={"room_type": "deluxe", "breakfast": True}
        )
        state_layer.save_guest_profile(profile)

        request = GuestMessage(guest_id="G123", message="What do you know about me?")
        response = guest_agent.process_message(request)

        # Should retrieve and use profile
        assert response.action == "retrieved_profile"

    def test_guest_never_talks_to_booking_directly(self):
        """Rule: Guest interacts ONLY with Guest Agent, never with Booking Agent directly"""
        # This test verifies the routing pattern
        # Guest asks about booking → Guest Agent → Orchestrator → Booking Agent
        request = GuestMessage(guest_id="G123", message="I want to book a room")
        response = guest_agent.process_message(request)

        # Must route through orchestrator, not direct to Booking
        assert response.action == "routed_to_orchestrator"

    def test_conversation_memory(self):
        """Guest Agent must remember conversation context"""
        guest_id = "G123"

        # First message
        msg1 = GuestMessage(guest_id=guest_id, message="I'm looking for a room")
        response1 = guest_agent.process_message(msg1)

        # Second message referencing first (implied context)
        msg2 = GuestMessage(guest_id=guest_id, message="For 2 nights")
        response2 = guest_agent.process_message(msg2)

        # Agent should understand the context without repeating "room"
        assert response2.confidence > 0.5  # Should be confident about context


class TestBookingFlow:
    """Test complete booking workflow (B1, B2, B3 with dependencies)"""

    def test_b1_availability_check(self):
        """B1: Booking Agent must check room availability"""
        # Setup: Create available rooms
        state_layer.update_room_status("101", RoomStatus.AVAILABLE)
        state_layer.update_room_status("102", RoomStatus.AVAILABLE)

        request = BookingRequest(
            guest_id="G123",
            check_in=datetime.now() + timedelta(days=1),
            check_out=datetime.now() + timedelta(days=3),
            room_type="standard"
        )

        response = booking_agent.check_availability(request)
        assert response.success is True
        assert len(response.available_rooms) > 0

    def test_b2_create_reservation(self):
        """B2: Booking Agent must create reservations"""
        request = BookingRequest(
            guest_id="G123",
            check_in=datetime.now() + timedelta(days=1),
            check_out=datetime.now() + timedelta(days=3),
            room_type="standard",
            room_id="101"
        )

        response = booking_agent.create_booking(request)
        assert response.success is True
        assert response.booking_id is not None
        assert response.status == BookingStatus.CONFIRMED

    def test_b3_pricing_with_revenue_dependency(self):
        """B3: Booking Agent must get pricing from Revenue Agent"""
        request = BookingRequest(
            guest_id="G123",
            check_in=datetime.now() + timedelta(days=1),
            check_out=datetime.now() + timedelta(days=4),  # 3 nights
            room_type="deluxe"
        )

        # Pricing should come from Revenue Agent
        response = booking_agent.calculate_pricing(request)
        assert response.total_price > 0
        assert response.price_breakdown is not None
        assert "nightly_rates" in response.price_breakdown

    def test_booking_triggers_operations(self):
        """Booking Agent must notify Operations Agent for room prep"""
        booking = BookingRequest(
            guest_id="G123",
            check_in=datetime.now() + timedelta(days=1),
            check_out=datetime.now() + timedelta(days=3),
            room_id="101"
        )

        # After booking confirmation
        booking_response = booking_agent.create_booking(booking)
        assert booking_response.success

        # Operations should have a task for room preparation
        tasks = state_layer.get_pending_tasks_for_room("101")
        assert any("prep" in task.task_type.lower() or "clean" in task.task_type.lower()
                  for task in tasks), "Should create room prep task"

    def test_overbooking_conflict_resolution(self):
        """Overbooking must trigger Decision Agent"""
        # Create conflicting bookings
        booking1 = BookingRequest(
            guest_id="G123",
            check_in=datetime.now() + timedelta(days=1),
            check_out=datetime.now() + timedelta(days=3),
            room_id="101"
        )
        booking2 = BookingRequest(
            guest_id="G456",
            check_in=datetime.now() + timedelta(days=2),  # Overlaps
            check_out=datetime.now() + timedelta(days=4),
            room_id="101"
        )

        # First booking succeeds
        response1 = booking_agent.create_booking(booking1)
        assert response1.success

        # Second booking should trigger conflict
        response2 = booking_agent.create_booking(booking2)
        assert response2.requires_decision  # Must escalate to Decision Agent


class TestOperationsAgent:
    """Test Operations Agent (O1, O2, O3)"""

    def test_o1_task_assignment(self):
        """O1: Operations Agent must assign tasks to staff"""
        request = ServiceRequest(
            guest_id="G123",
            room_id="101",
            service_type="housekeeping",
            urgency="normal"
        )

        response = operations_agent.process_service_request(request)
        assert response.success
        assert response.assigned_to is not None
        assert response.task_id is not None

    def test_o2_scheduling(self):
        """O2: Operations Agent must schedule tasks appropriately"""
        # High urgency request
        urgent = ServiceRequest(
            guest_id="G123",
            room_id="101",
            service_type="maintenance",
            urgency="high",  # AC broken
            details={"issue": "AC not working"}
        )

        response = operations_agent.process_service_request(urgent)
        assert response.scheduled_time < datetime.now() + timedelta(hours=1)

    def test_o3_execution_tracking(self):
        """O3: Operations Agent must track task completion"""
        # Create task
        request = ServiceRequest(
            guest_id="G123",
            room_id="101",
            service_type="housekeeping"
        )
        response = operations_agent.process_service_request(request)

        # Update task status
        task_id = response.task_id
        operations_agent.update_task_status(task_id, "in_progress")
        operations_agent.update_task_status(task_id, "completed")

        # Verify tracking
        task = state_layer.get_task(task_id)
        assert task.status == "completed"
        assert task.completed_at is not None

    def test_operations_reports_conflicts(self):
        """Operations Agent must report resource conflicts to Decision Agent"""
        # Two high-priority tasks for same staff
        task1 = ServiceRequest(
            guest_id="G123",
            room_id="101",
            service_type="maintenance",
            urgency="high"
        )
        task2 = ServiceRequest(
            guest_id="G456",
            room_id="102",
            service_type="maintenance",
            urgency="high"
        )

        # Assign both to same staff member
        response1 = operations_agent.process_service_request(task1)
        # Try to assign conflicting task
        response2 = operations_agent.process_service_request(task2)

        if response2.conflict_detected:
            assert response2.requires_decision  # Must escalate


class TestDecisionAgent:
    """Test Decision Agent (D1, D2, D3)"""

    def test_d1_edge_case_handling(self):
        """D1: Decision Agent handles edge cases"""
        escalation = EscalationRequest(
            source_agent="booking_agent",
            issue_type="edge_case",
            description="Guest requests 90-day stay with weekly billing",
            context={"guest_id": "G123", "duration": 90}
        )

        response = decision_agent.process_escalation(escalation)
        assert response.decision is not None
        assert response.resolution_strategy is not None

    def test_d2_policy_enforcement(self):
        """D2: Decision Agent enforces policies"""
        policy_check = {
            "policy": "max_occupancy",
            "guest_id": "G123",
            "room_id": "101",
            "requested_occupants": 5  # Exceeds policy
        }

        response = decision_agent.enforce_policy(
            policy_type="max_occupancy",
            agent_action=policy_check
        )

        assert response.policy_violation is True
        assert response.required_action in ["deny", "escalate", "override_with_approval"]

    def test_d3_human_escalation(self):
        """D3: Decision Agent escalates to humans when needed"""
        escalation = EscalationRequest(
            source_agent="guest_agent",
            issue_type="complaint",
            description="Guest extremely dissatisfied, demands manager",
            context={"sentiment": "very_negative", "guest_status": "vip"}
        )

        response = decision_agent.process_escalation(escalation)
        assert response.requires_human is True
        assert response.escalated_to is not None  # Should specify human role
        assert response.priority == "high"


class TestRevenueAgent:
    """Test Revenue Agent (R1, R2, R3)"""

    def test_r1_pricing_optimization(self):
        """R1: Revenue Agent optimizes pricing"""
        request = PricingRequest(
            room_type="deluxe",
            check_in=datetime.now() + timedelta(days=30),
            nights=2,
            guest_id="G123"
        )

        response = revenue_agent.optimize_pricing(request)
        assert response.recommended_price > 0
        assert response.confidence > 0.5
        assert response.factors is not None  # Should explain pricing factors

    def test_r2_demand_prediction(self):
        """R2: Revenue Agent predicts demand"""
        request = {
            "date_range": [
                datetime.now() + timedelta(days=1),
                datetime.now() + timedelta(days=30)
            ]
        }

        response = revenue_agent.predict_demand(request)
        assert response.demand_forecast is not None
        assert len(response.demand_forecast) > 0
        assert response.peak_dates is not None

    def test_r3_strategy_recommendations(self):
        """R3: Revenue Agent provides strategic recommendations"""
        context = {
            "period": "next_quarter",
            "goal": "increase_occupancy"
        }

        response = revenue_agent.generate_strategy(context)
        assert response.recommendations is not None
        assert len(response.recommendations) > 0
        assert response.expected_impact is not None


class TestOrchestrator:
    """Test Orchestrator routing and coordination"""

    def test_route_to_correct_agent(self):
        """Orchestrator routes to correct agent based on problem type"""
        test_cases = [
            ("book a room", "booking_agent"),
            ("price for suite", "revenue_agent"),
            ("room not clean", "operations_agent"),
            ("complaint about staff", "decision_agent"),
            ("general question", "guest_agent")
        ]

        for problem, expected_agent in test_cases:
            request = WorkflowRequest(
                source="guest_agent",
                problem_type="infer",
                problem_description=problem,
                guest_id="G123"
            )

            response = orchestrator.process_workflow_request(request)
            assert response.assigned_agent == expected_agent, f"Should route '{problem}' to {expected_agent}"

    def test_execution_order(self):
        """Orchestrator ensures correct execution order"""
        workflow = {
            "steps": [
                {"agent": "booking_agent", "action": "check_availability"},
                {"agent": "revenue_agent", "action": "get_pricing"},
                {"agent": "booking_agent", "action": "create_reservation"},
                {"agent": "operations_agent", "action": "schedule_prep"}
            ]
        }

        response = orchestrator.execute_workflow(workflow)
        assert response.execution_order == [0, 1, 2, 3]  # Sequential execution
        assert all(step["completed"] for step in response.step_results)

    def test_prevent_conflicts(self):
        """Orchestrator prevents agent conflicts"""
        # Two agents trying to modify same booking
        conflicting_requests = [
            WorkflowRequest(source="guest_agent", target="booking_agent", action="cancel_booking", booking_id="BK001"),
            WorkflowRequest(source="front_desk", target="booking_agent", action="modify_booking", booking_id="BK001")
        ]

        response = orchestrator.process_concurrent_requests(conflicting_requests)
        assert response.conflict_detected is True
        assert response.lock_acquired is True  # Orchestrator should lock resource


class TestDependencyRules:
    """Test Agent Dependency Rules (Rule 1, Rule 2, Rule 3)"""

    def test_rule1_no_random_agent_calls(self):
        """Rule 1: Agents do NOT randomly call each other"""
        # Guest Agent should NOT directly call Revenue Agent
        # Must go through Orchestrator
        guest_request = GuestMessage(guest_id="G123", message="What's the price?")
        response = guest_agent.process_message(guest_request)

        # Should route through orchestrator, not direct call
        assert response.action == "routed_to_orchestrator"

    def test_rule2_single_owner(self):
        """Rule 2: Every problem must have ONE owner agent"""
        # Booking problem should be owned by Booking Agent
        request = WorkflowRequest(
            source="guest_agent",
            problem_type="booking",
            problem_description="Guest wants to book room 101",
            guest_id="G123"
        )

        response = orchestrator.process_workflow_request(request)
        assert response.owner_agent == "booking_agent"
        # Should not have multiple owners
        assert len(response.coordinating_agents) == 0 or response.coordinating_agents is None

    def test_rule3_decision_agent_not_default(self):
        """Rule 3: Decision Agent is NOT default"""
        # Normal booking should NOT go to Decision Agent
        request = BookingRequest(
            guest_id="G123",
            check_in=datetime.now() + timedelta(days=1),
            check_out=datetime.now() + timedelta(days=3),
            room_id="101"
        )

        response = booking_agent.process_booking_request(request)
        assert response.escalated_to_decision is False  # Normal flow, no escalation

    def test_decision_agent_only_for_conflicts(self):
        """Decision Agent only used for conflicts/ambiguity/exceptions"""
        # Conflict scenario
        escalation = EscalationRequest(
            source_agent="booking_agent",
            issue_type="conflict",
            description="Double booking detected"
        )

        response = decision_agent.process_escalation(escalation)
        # Decision Agent should handle this
        assert response.decision is not None


class TestActorInteractions:
    """Test Actor → Agent Interaction Map"""

    def test_guest_only_talks_to_guest_agent(self):
        """Guest interacts ONLY with Guest Agent"""
        # Guest sends message
        guest_msg = GuestMessage(guest_id="G123", message="I need help")
        response = guest_agent.process_message(guest_msg)

        # Should get response from Guest Agent
        assert response is not None
        assert response.message is not None

        # Guest should NOT directly interact with other agents
        # (This is enforced by architecture, not testable at API level)

    def test_frontline_staff_interactions(self):
        """Frontline Staff interacts with Guest Agent (override), Booking, Decision"""
        # Front desk override
        override_request = {
            "actor": "front_desk",
            "action": "override_booking",
            "booking_id": "BK001",
            "changes": {"room_id": "102"}
        }

        # Should go through proper channels
        response = booking_agent.handle_staff_override(override_request)
        assert response.approved is True or response.requires_decision is True

    def test_management_interactions(self):
        """Management interacts with Decision and Revenue Agents"""
        # Manager resolves escalation
        resolution = {
            "actor": "manager",
            "escalation_id": "ESC001",
            "decision": "approve_override",
            "reason": "VIP guest"
        }

        response = decision_agent.process_human_decision(resolution)
        assert response.executed is True

    def test_system_admin_interactions(self):
        """System/Admin interacts with Orchestrator and State Layer"""
        # Admin configures orchestrator
        config = {
            "actor": "admin",
            "action": "update_routing_rules",
            "rules": {"vip_guest": "priority_booking"}
        }

        response = orchestrator.update_configuration(config)
        assert response.applied is True


class TestWorkflowIntegration:
    """End-to-end workflow integration tests"""

    def test_complete_booking_workflow(self):
        """Test complete booking workflow from Guest to Confirmation"""
        # Step 1: Guest inquiry
        guest_msg = GuestMessage(guest_id="G123", message="I want to book a deluxe room for 2 nights")
        guest_response = guest_agent.process_message(guest_msg)

        assert guest_response.action == "routed_to_orchestrator"

        # Step 2: Orchestrator routes to Booking Agent
        workflow_request = WorkflowRequest(
            source="guest_agent",
            problem_type="booking",
            guest_id="G123",
            intent="book_room",
            details={"room_type": "deluxe", "nights": 2}
        )
        orch_response = orchestrator.process_workflow_request(workflow_request)

        assert orch_response.assigned_agent == "booking_agent"

        # Step 3: Booking Agent checks availability (B1)
        booking_req = BookingRequest(
            guest_id="G123",
            room_type="deluxe",
            nights=2
        )
        avail_response = booking_agent.check_availability(booking_req)

        assert avail_response.success
        assert len(avail_response.available_rooms) > 0

        # Step 4: Revenue Agent provides pricing (R1, dependency)
        pricing_req = PricingRequest(
            room_type="deluxe",
            nights=2,
            guest_id="G123"
        )
        pricing_response = revenue_agent.optimize_pricing(pricing_req)

        assert pricing_response.recommended_price > 0

        # Step 5: Booking Agent creates reservation (B2)
        booking_req.room_id = avail_response.available_rooms[0]
        booking_req.price = pricing_response.recommended_price
        booking_response = booking_agent.create_booking(booking_req)

        assert booking_response.success
        assert booking_response.status == BookingStatus.CONFIRMED

        # Step 6: Operations Agent schedules room prep (O1, triggered)
        # Verify task was created
        tasks = state_layer.get_pending_tasks_for_room(booking_req.room_id)
        assert any("prep" in t.task_type.lower() for t in tasks)

        # Step 7: Guest Agent confirms to guest (G2)
        confirmation_msg = f"Your booking is confirmed! Room {booking_req.room_id} for 2 nights. Total: ${booking_response.total_price}"
        assert booking_response.confirmation_sent is True or booking_response.booking_id is not None

    def test_complaint_escalation_workflow(self):
        """Test complaint workflow from Guest to Manager resolution"""
        # Step 1: Guest complaint
        complaint = GuestMessage(guest_id="G123", message="I'm very unhappy with the service!")
        guest_response = guest_agent.process_message(complaint)

        assert guest_response.action in ["routed_to_orchestrator", "escalation_detected"]

        # Step 2: Decision Agent evaluates
        escalation = EscalationRequest(
            source_agent="guest_agent",
            issue_type="complaint",
            guest_id="G123",
            severity="high"
        )
        decision_response = decision_agent.process_escalation(escalation)

        assert decision_response.requires_human is True
        assert decision_response.escalated_to == "manager"

        # Step 3: Manager resolution
        # (In real system, this would be async human input)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
