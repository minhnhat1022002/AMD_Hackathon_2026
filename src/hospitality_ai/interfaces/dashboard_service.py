"""Dashboard Service for Front Desk Interface.

Simple dict-based implementation for demo purposes.
"""

from __future__ import annotations

from typing import Dict, List, Any
import datetime
import uuid

from ..agents.booking_agent import booking_agent
from ..agents.decision_agent import decision_agent


class DashboardService:
    """Front Desk Dashboard service with simple in-memory storage."""
    
    def __init__(self, container: Dict[str, Any]):
        """Initialize dashboard service with dependency container."""
        self.container = container
        self._init_mock_data()
    
    def _init_mock_data(self) -> None:
        """Initialize mock data for demo."""
        # Mock reservations
        self.reservations = {
            "R001": {
                "id": "R001",
                "guest_name": "John Smith",
                "check_in": "2024-01-15",
                "check_out": "2024-01-17",
                "room_type": "deluxe",
                "price": 240,
                "status": "confirmed"
            },
            "R002": {
                "id": "R002", 
                "guest_name": "Sarah Johnson",
                "check_in": "2024-01-16",
                "check_out": "2024-01-18",
                "room_type": "standard",
                "price": 160,
                "status": "pending"
            },
            "R003": {
                "id": "R003",
                "guest_name": "Mike Chen",
                "check_in": "2024-01-14",
                "check_out": "2024-01-16",
                "room_type": "suite",
                "price": 400,
                "status": "confirmed"
            }
        }
        
        # Mock guest activity
        self.guest_activity = {
            "G123": {
                "guest_id": "G123",
                "name": "John Smith",
                "status": "active",
                "last_message": "Do you have rooms tomorrow?",
                "last_activity": "2 minutes ago",
                "reservation_id": "R001"
            },
            "G456": {
                "guest_id": "G456",
                "name": "Sarah Johnson", 
                "status": "escalated",
                "last_message": "Room is dirty, I need help!",
                "last_activity": "5 minutes ago",
                "case_id": "C001",
                "reservation_id": "R002"
            },
            "G789": {
                "guest_id": "G789",
                "name": "Mike Chen",
                "status": "active",
                "last_message": "Book 2 nights for me",
                "last_activity": "10 minutes ago",
                "reservation_id": "R003"
            }
        }
        
        # Mock decision queue
        self.decision_cases = {
            "C001": {
                "id": "C001",
                "type": "complaint",
                "priority": "urgent",
                "guest_id": "G456",
                "description": "Guest reports room cleanliness issues",
                "created_at": "10 minutes ago",
                "status": "pending",
                "history": [
                    {"timestamp": "10:30 AM", "action": "Case created from guest chat"},
                    {"timestamp": "10:32 AM", "action": "Escalated to front desk"}
                ]
            },
            "C002": {
                "id": "C002",
                "type": "booking_issue",
                "priority": "pending",
                "guest_id": "G789",
                "description": "Guest wants to modify reservation dates",
                "created_at": "25 minutes ago",
                "status": "pending",
                "history": [
                    {"timestamp": "10:15 AM", "action": "Case created from booking agent"},
                    {"timestamp": "10:20 AM", "action": "Awaiting staff review"}
                ]
            }
        }
    
    def get_reservations(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all reservations."""
        return {"reservations": list(self.reservations.values())}
    
    def override_booking(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Override a booking reservation."""
        reservation_id = request.get("res_id")
        
        if not reservation_id or reservation_id not in self.reservations:
            raise ValueError(f"Reservation {reservation_id} not found")
        
        # Update reservation
        reservation = self.reservations[reservation_id]
        reservation["guest_name"] = request.get("guest_name", reservation["guest_name"])
        reservation["check_in"] = request.get("checkin-date", reservation["check_in"])
        reservation["check_out"] = request.get("checkout-date", reservation["check_out"])
        reservation["room_type"] = request.get("room-type", reservation["room_type"])
        
        # Update price based on room type
        room_prices = {"standard": 80, "deluxe": 120, "suite": 200}
        nights = self._calculate_nights(reservation["check_in"], reservation["check_out"])
        reservation["price"] = room_prices.get(reservation["room_type"], 100) * nights
        
        # Integrate with Booking Agent for validation
        try:
            from ..agents.booking_agent import BookingRequest, BookingResponse
            booking_request = BookingRequest(
                guest_id=self._find_guest_by_reservation(reservation_id),
                check_in=reservation["check_in"],
                check_out=reservation["check_out"],
                room_type=reservation["room_type"]
            )
            
            # Validate with Booking Agent (simplified for demo)
            # In real implementation, this would call booking_agent.process_booking_request()
            # For now, just mark as successful override
            reservation["status"] = "modified"
            reservation["modified_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
        except Exception as e:
            # Log error but don't fail the override for demo
            print(f"Booking agent integration warning: {e}")
        
        return {"updated_reservation": reservation}
    
    def get_guest_activity(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get guest activity for monitoring."""
        return {"guests": list(self.guest_activity.values())}
    
    def get_decision_queue(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get decision queue for front desk."""
        return {"cases": list(self.decision_cases.values())}
    
    def resolve_case(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a decision case."""
        action = request.get("action")
        
        if not action:
            raise ValueError("Action is required")
        
        # For demo, just mark first pending case as resolved
        for case_id, case in self.decision_cases.items():
            if case["status"] == "pending":
                case["status"] = "resolved"
                case["resolved_at"] = datetime.datetime.now().strftime("%I:%M %p")
                case["resolved_by"] = "FD001"
                case["resolution"] = action
                
                # Integrate with Decision Agent (simplified for demo)
                try:
                    from ..agents.decision_agent import DecisionRequest, DecisionResponse
                    decision_request = DecisionRequest(
                        case_id=case_id,
                        guest_id=case["guest_id"],
                        case_type=case["type"],
                        action=action,
                        priority=case["priority"]
                    )
                    
                    # In real implementation, this would call decision_agent.process_decision()
                    # For now, just log the integration
                    print(f"Decision Agent integration: {decision_request}")
                    
                except Exception as e:
                    # Log error but don't fail resolution for demo
                    print(f"Decision agent integration warning: {e}")
                
                # Update guest status if this was an escalated case
                guest_id = case["guest_id"]
                if guest_id in self.guest_activity:
                    self.guest_activity[guest_id]["status"] = "active"
                    self.guest_activity[guest_id]["last_message"] = f"Case resolved: {action}"
                    self.guest_activity[guest_id]["last_activity"] = "Just now"
                
                return {"resolved_case": case}
        
        raise ValueError("No pending cases found")
    
    def _calculate_nights(self, check_in: str, check_out: str) -> int:
        """Calculate number of nights between dates."""
        try:
            check_in_date = datetime.datetime.strptime(check_in, "%Y-%m-%d")
            check_out_date = datetime.datetime.strptime(check_out, "%Y-%m-%d")
            return (check_out_date - check_in_date).days
        except ValueError:
            return 1  # Default to 1 night if date parsing fails
    
    def _find_guest_by_reservation(self, reservation_id: str) -> str:
        """Find guest ID by reservation ID."""
        for guest_id, guest_data in self.guest_activity.items():
            if guest_data.get("reservation_id") == reservation_id:
                return guest_id
        return "UNKNOWN"  # Fallback for demo
