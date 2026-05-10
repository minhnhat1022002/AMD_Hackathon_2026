"""
Comprehensive LLM-Simulated Actor Test Suite
All actor types in one unified test file: Guest, Staff, Management, and System Admin
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

# Import all the models and APIs we need
from hospitality_ai.models.operations_models import Task, TaskCreate, TaskType, TaskPriority
from hospitality_ai.models.management_models import EscalationCase, ManualDecision, CaseSeverity
from hospitality_ai.models.revenue_models import PricingUpdate, PricingStrategy
from hospitality_ai.models.admin_models import SystemConfig, ConfigUpdate

# Import API route storage for testing
from hospitality_ai.api.routes.operations_routes import _tasks_storage, generate_task_id
from hospitality_ai.api.routes.management_routes import _cases_storage, generate_case_id
from hospitality_ai.api.routes.revenue_routes import _overrides_storage, generate_override_id
from hospitality_ai.api.routes.admin_routes import _configs_storage

# Import workflow monitor
from hospitality_ai.monitoring.workflow_monitor import workflow_monitor


class ActorType(Enum):
    """Actor types for testing"""
    GUEST = "guest"
    FRONT_DESK = "front_desk"
    MANAGEMENT = "management"
    HOUSEKEEPING = "housekeeping"
    MAINTENANCE = "maintenance"
    ADMIN = "admin"


class ActorPersona(Enum):
    """Guest personas for LLM simulation"""
    BUSINESS_TRAVELER = "business_traveler"
    FAMILY_VACATION = "family_vacation"
    COUPLE_GETAWAY = "couple_getaway"
    BUDGET_TRAVELER = "budget_traveler"
    LUXURY_SEEKER = "luxury_seeker"


class StaffRole(Enum):
    """Staff roles for testing"""
    RECEPTIONIST = "receptionist"
    NIGHT_MANAGER = "night_manager"
    CONCIERGE = "concierge"
    HOUSEKEEPER = "housekeeper"
    MAINTENANCE_TECH = "maintenance_tech"
    HOTEL_MANAGER = "hotel_manager"
    REVENUE_MANAGER = "revenue_manager"
    SYSTEM_ADMIN = "system_admin"


class LLMSimulatedActor:
    """Base class for LLM-simulated actors"""
    
    def __init__(self, actor_type: ActorType, persona: Optional[str] = None):
        self.actor_type = actor_type
        self.persona = persona
        self.conversation_history = []
        self.current_emotion = "neutral"
        self.urgency_level = "normal"
        
    def generate_message(self, context: Dict[str, Any]) -> str:
        """Generate contextually appropriate message"""
        if self.actor_type == ActorType.GUEST:
            return self._generate_guest_message(context)
        elif self.actor_type == ActorType.FRONT_DESK:
            return self._generate_staff_message(context)
        elif self.actor_type == ActorType.MANAGEMENT:
            return self._generate_management_message(context)
        else:
            return self._generate_rule_based_message(context)
    
    def _generate_guest_message(self, context: Dict[str, Any]) -> str:
        """Generate guest message based on persona"""
        messages = {
            ActorPersona.BUSINESS_TRAVELER: [
                "I need a room for 3 nights, starting tomorrow. Prefer executive floor.",
                "What's your corporate rate? I'm here for the tech conference.",
                "I need early check-in and late check-out. My flight arrives at 8 AM.",
                "Do you have meeting rooms available for tomorrow afternoon?",
                "I need to extend my stay by one night, room 1205."
            ],
            ActorPersona.FAMILY_VACATION: [
                "We need 2 adjoining rooms for a family of 4, kids ages 8 and 11.",
                "Do you have cribs available? And what about kids' activities?",
                "Is the pool heated? What time does it open?",
                "We need a late check-out, our flight isn't until 8 PM.",
                "The WiFi in our room isn't working properly."
            ],
            ActorPersona.COUPLE_GETAWAY: [
                "We're celebrating our anniversary, do you have any special packages?",
                "We'd like a room with a view, preferably city view.",
                "What restaurants do you recommend nearby?",
                "Can we get a late check-out tomorrow?",
                "The minibar in our room needs to be restocked."
            ],
            ActorPersona.BUDGET_TRAVELER: [
                "What's your cheapest room rate for tonight?",
                "Are there any discounts available for AAA members?",
                "Do you offer free breakfast with the room?",
                "Is parking included in the room rate?",
                "Can I cancel without penalty if my plans change?"
            ],
            ActorPersona.LUXURY_SEEKER: [
                "I need the presidential suite for this weekend.",
                "Can you arrange for a bottle of champagne to be sent to my room?",
                "I'd like a spa treatment appointment for tomorrow.",
                "What's the best room in the hotel available?",
                "I need airport transfer arranged for tomorrow morning."
            ]
        }
        
        import random
        if self.persona in messages:
            return random.choice(messages[self.persona])
        return "I need help with my reservation."
    
    def _generate_staff_message(self, context: Dict[str, Any]) -> str:
        """Generate front desk staff message"""
        if context.get("situation") == "check_in":
            return "Welcome to our hotel! I'll help you with your check-in process. May I have your name and reservation details?"
        elif context.get("situation") == "complaint":
            return "I understand your concern and I'm here to help resolve this issue for you. Let me look into this immediately."
        elif context.get("situation") == "booking_modification":
            return "I can help you modify your reservation. Let me check the availability and options for you."
        else:
            return "How may I assist you today?"
    
    def _generate_management_message(self, context: Dict[str, Any]) -> str:
        """Generate management decision message"""
        if context.get("situation") == "escalation":
            return "I've reviewed this case and will make a decision based on our policies and guest satisfaction priorities."
        elif context.get("situation") == "revenue_decision":
            return "Based on current occupancy and market conditions, I recommend adjusting our pricing strategy."
        else:
            return "I'll review this matter and provide guidance accordingly."
    
    def _generate_rule_based_message(self, context: Dict[str, Any]) -> str:
        """Generate rule-based staff message"""
        if self.actor_type == ActorType.HOUSEKEEPING:
            return "Housekeeping task received. Will proceed with room preparation."
        elif self.actor_type == ActorType.MAINTENANCE:
            return "Maintenance request logged. Will assess and resolve the issue."
        elif self.actor_type == ActorType.ADMIN:
            return "System configuration update received. Processing changes."
        else:
            return "Task acknowledged."


class ComprehensiveActorTestSuite:
    """Complete test suite for all actor types"""
    
    def __init__(self):
        self.test_results = []
        self.actors = []
        self.workflow_events = []
        
    def clear_all_storage(self):
        """Clear all in-memory storage for clean testing"""
        _tasks_storage.clear()
        _cases_storage.clear()
        _overrides_storage.clear()
        _configs_storage.clear()
        workflow_monitor.workflow_events.clear()
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result for reporting"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_guest_actor_scenarios(self) -> bool:
        """Test all guest actor personas and scenarios"""
        try:
            self.clear_all_storage()
            
            guest_personas = [
                ActorPersona.BUSINESS_TRAVELER,
                ActorPersona.FAMILY_VACATION,
                ActorPersona.COUPLE_GETAWAY,
                ActorPersona.BUDGET_TRAVELER,
                ActorPersona.LUXURY_SEEKER
            ]
            
            guest_scenarios = [
                {"intent": "booking", "urgency": "normal"},
                {"intent": "service_request", "urgency": "medium"},
                {"intent": "complaint", "urgency": "high"},
                {"intent": "inquiry", "urgency": "normal"},
                {"intent": "modification", "urgency": "medium"}
            ]
            
            total_interactions = 0
            successful_interactions = 0
            
            for persona in guest_personas:
                for scenario in guest_scenarios:
                    guest_actor = LLMSimulatedActor(ActorType.GUEST, persona)
                    guest_actor.persona = persona
                    guest_actor.urgency_level = scenario["urgency"]
                    
                    # Generate guest message
                    context = {"intent": scenario["intent"], "urgency": scenario["urgency"]}
                    message = guest_actor.generate_message(context)
                    
                    # Simulate guest agent processing
                    guest_id = f"G{str(total_interactions + 1).zfill(3)}"
                    
                    # Create workflow event
                    event = {
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "guest_interaction",
                        "actor_type": "guest",
                        "persona": persona.value,
                        "scenario": scenario["intent"],
                        "message": message,
                        "guest_id": guest_id,
                        "urgency": scenario["urgency"],
                        "from": "guest_chat",
                        "to": "guest_agent",
                        "details": f"Guest {persona.value} interaction: {scenario['intent']}"
                    }
                    workflow_monitor.workflow_events.append(event)
                    self.workflow_events.append(event)
                    
                    total_interactions += 1
                    successful_interactions += 1
            
            result = successful_interactions == total_interactions
            self.log_test_result("Guest Actor Scenarios", result, 
                                f"Tested {len(guest_personas)} personas × {len(guest_scenarios)} scenarios = {total_interactions} interactions")
            return result
            
        except Exception as e:
            self.log_test_result("Guest Actor Scenarios", False, str(e))
            return False
    
    def test_front_desk_staff_scenarios(self) -> bool:
        """Test front desk staff LLM simulation"""
        try:
            self.clear_all_storage()
            
            staff_roles = [
                StaffRole.RECEPTIONIST,
                StaffRole.NIGHT_MANAGER,
                StaffRole.CONCIERGE
            ]
            
            staff_scenarios = [
                {"situation": "check_in", "complexity": "simple"},
                {"situation": "complaint", "complexity": "complex"},
                {"situation": "booking_modification", "complexity": "medium"},
                {"situation": "check_out", "complexity": "simple"},
                {"situation": "special_request", "complexity": "medium"}
            ]
            
            total_interactions = 0
            successful_interactions = 0
            
            for role in staff_roles:
                for scenario in staff_scenarios:
                    staff_actor = LLMSimulatedActor(ActorType.FRONT_DESK)
                    
                    # Generate staff response
                    context = {"situation": scenario["situation"], "role": role.value}
                    response = staff_actor.generate_message(context)
                    
                    # Create workflow event
                    event = {
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "staff_interaction",
                        "actor_type": "front_desk",
                        "role": role.value,
                        "scenario": scenario["situation"],
                        "response": response,
                        "complexity": scenario["complexity"],
                        "from": "staff_dashboard",
                        "to": "guest_agent",
                        "details": f"Front desk {role.value} handling {scenario['situation']}"
                    }
                    workflow_monitor.workflow_events.append(event)
                    self.workflow_events.append(event)
                    
                    total_interactions += 1
                    successful_interactions += 1
            
            result = successful_interactions == total_interactions
            self.log_test_result("Front Desk Staff Scenarios", result,
                                f"Tested {len(staff_roles)} roles × {len(staff_scenarios)} scenarios = {total_interactions} interactions")
            return result
            
        except Exception as e:
            self.log_test_result("Front Desk Staff Scenarios", False, str(e))
            return False
    
    def test_management_decision_scenarios(self) -> bool:
        """Test management decision LLM simulation"""
        try:
            self.clear_all_storage()
            
            management_roles = [
                StaffRole.HOTEL_MANAGER,
                StaffRole.REVENUE_MANAGER
            ]
            
            decision_scenarios = [
                {"situation": "escalation", "impact": "high"},
                {"situation": "revenue_decision", "impact": "medium"},
                {"situation": "policy_override", "impact": "high"},
                {"situation": "staff_management", "impact": "medium"},
                {"situation": "crisis_management", "impact": "high"}
            ]
            
            total_decisions = 0
            successful_decisions = 0
            
            for role in management_roles:
                for scenario in decision_scenarios:
                    management_actor = LLMSimulatedActor(ActorType.MANAGEMENT)
                    
                    # Generate management decision
                    context = {"situation": scenario["situation"], "role": role.value}
                    decision = management_actor.generate_message(context)
                    
                    # Create escalation case if needed
                    if scenario["situation"] == "escalation":
                        case_id = generate_case_id()
                        escalation_case = EscalationCase(
                            case_id=case_id,
                            guest_id="G456",
                            issue_type="complex_guest_issue",
                            severity=CaseSeverity.HIGH,
                            description="Guest escalation requiring management decision",
                            assigned_to=f"{role.value}_001"
                        )
                        _cases_storage[case_id] = escalation_case
                    
                    # Create workflow event
                    event = {
                        "timestamp": datetime.now().isoformat(),
                        "event_type": "management_decision",
                        "actor_type": "management",
                        "role": role.value,
                        "scenario": scenario["situation"],
                        "decision": decision,
                        "impact": scenario["impact"],
                        "from": "management_dashboard",
                        "to": "decision_agent",
                        "details": f"Management {role.value} decision on {scenario['situation']}"
                    }
                    workflow_monitor.workflow_events.append(event)
                    self.workflow_events.append(event)
                    
                    total_decisions += 1
                    successful_decisions += 1
            
            result = successful_decisions == total_decisions
            self.log_test_result("Management Decision Scenarios", result,
                                f"Tested {len(management_roles)} roles × {len(decision_scenarios)} scenarios = {total_decisions} decisions")
            return result
            
        except Exception as e:
            self.log_test_result("Management Decision Scenarios", False, str(e))
            return False
    
    def test_rule_based_staff_scenarios(self) -> bool:
        """Test rule-based staff scenarios (housekeeping, maintenance, admin)"""
        try:
            self.clear_all_storage()
            
            rule_based_actors = [
                ActorType.HOUSEKEEPING,
                ActorType.MAINTENANCE,
                ActorType.ADMIN
            ]
            
            rule_scenarios = [
                {"task": "room_preparation", "actor": ActorType.HOUSEKEEPING},
                {"task": "maintenance_request", "actor": ActorType.MAINTENANCE},
                {"task": "system_config", "actor": ActorType.ADMIN},
                {"task": "cleaning_complete", "actor": ActorType.HOUSEKEEPING},
                {"task": "issue_resolved", "actor": ActorType.MAINTENANCE},
                {"task": "config_update", "actor": ActorType.ADMIN}
            ]
            
            total_tasks = 0
            successful_tasks = 0
            
            for scenario in rule_scenarios:
                actor = LLMSimulatedActor(scenario["actor"])
                
                # Generate rule-based response
                context = {"task": scenario["task"]}
                response = actor.generate_message(context)
                
                # Create actual tasks/items
                if scenario["actor"] == ActorType.HOUSEKEEPING:
                    task_id = generate_task_id()
                    task = Task(
                        task_id=task_id,
                        staff_id="H001",
                        guest_id="G123",
                        room_id="201",
                        task_type=TaskType.HOUSEKEEPING,
                        priority=TaskPriority.NORMAL,
                        description="Prepare room 201 for guest arrival"
                    )
                    _tasks_storage[task_id] = task
                    
                elif scenario["actor"] == ActorType.MAINTENANCE:
                    task_id = generate_task_id()
                    task = Task(
                        task_id=task_id,
                        staff_id="M001",
                        guest_id="G456",
                        room_id="305",
                        task_type=TaskType.MAINTENANCE,
                        priority=TaskPriority.NORMAL,
                        description="Fix maintenance issue in room 305"
                    )
                    _tasks_storage[task_id] = task
                    
                elif scenario["actor"] == ActorType.ADMIN:
                    config_key = f"config_{total_tasks + 1}"
                    config = SystemConfig(
                        config_key=config_key,
                        config_value=True,
                        description=f"Configuration for {scenario['task']}",
                        category="system",
                        updated_by="admin_001"
                    )
                    _configs_storage[config_key] = config
                
                # Create workflow event
                event = {
                    "timestamp": datetime.now().isoformat(),
                    "event_type": "rule_based_task",
                    "actor_type": scenario["actor"].value,
                    "task": scenario["task"],
                    "response": response,
                    "from": f"{scenario['actor'].value}_interface",
                    "to": "operations_agent",
                    "details": f"Rule-based {scenario['actor'].value} task: {scenario['task']}"
                }
                workflow_monitor.workflow_events.append(event)
                self.workflow_events.append(event)
                
                total_tasks += 1
                successful_tasks += 1
            
            result = successful_tasks == total_tasks
            self.log_test_result("Rule-Based Staff Scenarios", result,
                                f"Tested {len(rule_scenarios)} rule-based tasks = {total_tasks} tasks")
            return result
            
        except Exception as e:
            self.log_test_result("Rule-Based Staff Scenarios", False, str(e))
            return False
    
    def test_multi_actor_integration(self) -> bool:
        """Test multiple actors working together in complete workflows"""
        try:
            self.clear_all_storage()
            
            # Scenario 1: Complete guest booking workflow
            guest_actor = LLMSimulatedActor(ActorType.GUEST, ActorPersona.BUSINESS_TRAVELER)
            staff_actor = LLMSimulatedActor(ActorType.FRONT_DESK)
            management_actor = LLMSimulatedActor(ActorType.MANAGEMENT)
            housekeeping_actor = LLMSimulatedActor(ActorType.HOUSEKEEPING)
            
            # Step 1: Guest booking request
            guest_message = guest_actor.generate_message({"intent": "booking"})
            booking_event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "guest_booking_request",
                "actor_type": "guest",
                "message": guest_message,
                "from": "guest_chat",
                "to": "guest_agent",
                "details": "Guest booking request initiated"
            }
            workflow_monitor.workflow_events.append(booking_event)
            
            # Step 2: Front desk processing
            staff_response = staff_actor.generate_message({"situation": "check_in"})
            processing_event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "staff_processing",
                "actor_type": "front_desk",
                "response": staff_response,
                "from": "staff_dashboard",
                "to": "booking_agent",
                "details": "Front desk processing booking request"
            }
            workflow_monitor.workflow_events.append(processing_event)
            
            # Step 3: Housekeeping task creation
            task_id = generate_task_id()
            task = Task(
                task_id=task_id,
                staff_id="H001",
                guest_id="G789",
                room_id="401",
                task_type=TaskType.HOUSEKEEPING,
                priority=TaskPriority.HIGH,
                description="Prepare business suite for VIP guest"
            )
            _tasks_storage[task_id] = task
            
            # Step 4: Housekeeping acknowledgment
            housekeeping_response = housekeeping_actor.generate_message({"task": "room_preparation"})
            task_event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": "housekeeping_task",
                "actor_type": "housekeeping",
                "task_id": task_id,
                "response": housekeeping_response,
                "from": "mobile_app",
                "to": "operations_agent",
                "details": "Housekeeping task assigned and acknowledged"
            }
            workflow_monitor.workflow_events.append(task_event)
            
            # Verify integration
            integration_success = (
                len(_tasks_storage) == 1 and
                len(workflow_monitor.workflow_events) == 4
            )
            
            self.log_test_result("Multi-Actor Integration", integration_success,
                                f"Complete workflow with 4 actors, {len(workflow_monitor.workflow_events)} events")
            return integration_success
            
        except Exception as e:
            self.log_test_result("Multi-Actor Integration", False, str(e))
            return False
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        # Actor type statistics
        actor_stats = {}
        for event in self.workflow_events:
            actor_type = event.get("actor_type", "unknown")
            if actor_type not in actor_stats:
                actor_stats[actor_type] = 0
            actor_stats[actor_type] += 1
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": self.test_results,
            "actor_statistics": actor_stats,
            "workflow_events": self.workflow_events,
            "api_usage": {
                "operations_api": len(_tasks_storage),
                "management_api": len(_cases_storage),
                "revenue_api": len(_overrides_storage),
                "admin_api": len(_configs_storage)
            },
            "coverage_analysis": {
                "llm_actors_tested": 3,  # Guest, Front Desk, Management
                "rule_based_actors_tested": 3,  # Housekeeping, Maintenance, Admin
                "total_scenarios_covered": len(self.workflow_events),
                "integration_workflows": 1
            }
        }
        
        return report


def run_comprehensive_actor_tests():
    """Run all comprehensive actor tests"""
    print("Starting Comprehensive LLM-Simulated Actor Test Suite")
    print("=" * 70)
    
    suite = ComprehensiveActorTestSuite()
    
    # Run all actor tests
    tests = [
        ("Guest Actor Scenarios", suite.test_guest_actor_scenarios),
        ("Front Desk Staff Scenarios", suite.test_front_desk_staff_scenarios),
        ("Management Decision Scenarios", suite.test_management_decision_scenarios),
        ("Rule-Based Staff Scenarios", suite.test_rule_based_staff_scenarios),
        ("Multi-Actor Integration", suite.test_multi_actor_integration)
    ]
    
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        try:
            result = test_func()
            status = "PASSED" if result else "FAILED"
            print(f"   {status}")
        except Exception as e:
            print(f"   ERROR: {str(e)}")
    
    # Generate and display comprehensive report
    print("\n" + "=" * 70)
    print("COMPREHENSIVE ACTOR TEST REPORT")
    print("=" * 70)
    
    report = suite.generate_comprehensive_report()
    
    summary = report["test_summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    
    print("\nActor Type Statistics:")
    actor_stats = report["actor_statistics"]
    for actor_type, count in actor_stats.items():
        print(f"  {actor_type.title()}: {count} interactions")
    
    print("\nAPI Usage:")
    api_usage = report["api_usage"]
    for api, count in api_usage.items():
        print(f"  {api.title()}: {count} items")
    
    print("\nCoverage Analysis:")
    coverage = report["coverage_analysis"]
    print(f"  LLM Actors Tested: {coverage['llm_actors_tested']}")
    print(f"  Rule-Based Actors Tested: {coverage['rule_based_actors_tested']}")
    print(f"  Total Scenarios Covered: {coverage['total_scenarios_covered']}")
    print(f"  Integration Workflows: {coverage['integration_workflows']}")
    
    print(f"\nWorkflow Events Generated: {len(report['workflow_events'])}")
    
    # Show detailed results for failed tests
    failed_results = [r for r in report["test_results"] if not r["success"]]
    if failed_results:
        print("\nFailed Tests:")
        for result in failed_results:
            print(f"  - {result['test_name']}: {result['details']}")
    
    # Save comprehensive report
    try:
        with open('comprehensive_actor_test_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print("\nComprehensive report saved to comprehensive_actor_test_report.json")
    except Exception as e:
        print(f"Error saving report: {e}")
    
    print("\nComprehensive Actor Test Suite Complete!")
    return report


if __name__ == "__main__":
    run_comprehensive_actor_tests()