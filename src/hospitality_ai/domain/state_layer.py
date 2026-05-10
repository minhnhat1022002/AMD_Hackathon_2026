"""
State Layer - Central data hub for all agents.

This module provides in-memory state management with real-time event notifications.
No database dependency - designed for AI workflow demonstration.
"""

import threading
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
import logging

logger = logging.getLogger(__name__)

@dataclass
class CustomerMemory:
    """Customer memory for persistent storage across sessions."""
    customer_id: str
    personal_info: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    stay_history: List[Dict] = field(default_factory=list)
    service_requests: List[Dict] = field(default_factory=list)
    complaint_history: List[Dict] = field(default_factory=list)
    loyalty_info: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class RoomStatus(Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    CLEANING = "cleaning"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class GuestProfile:
    """Guest profile data model."""
    guest_id: str
    name: str
    email: str
    phone: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    communication_style: str = "formal"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Room:
    """Room data model."""
    room_id: str
    room_type: str
    status: RoomStatus
    base_price: float
    current_price: float
    floor: int
    amenities: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class Booking:
    """Booking data model."""
    booking_id: str
    guest_id: str
    room_id: str
    check_in: datetime
    check_out: datetime
    status: BookingStatus
    total_price: float
    special_requests: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """Task data model."""
    task_id: str
    task_type: str
    assigned_to: str
    room_id: Optional[str]
    priority: Priority
    status: TaskStatus
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class PricingRule:
    """Pricing rule data model."""
    room_type: str
    base_price: float
    demand_multiplier: float = 1.0
    seasonal_adjustment: float = 1.0
    last_updated: datetime = field(default_factory=datetime.now)


class StateLayer:
    """
    Central state management for all agents.
    
    Provides thread-safe in-memory storage with real-time event notifications.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Data stores
        self._guest_profiles: Dict[str, GuestProfile] = {}
        self._rooms: Dict[str, Room] = {}
        self._bookings: Dict[str, Booking] = {}
        self._tasks: Dict[str, Task] = {}
        self._pricing_rules: Dict[str, PricingRule] = {}
        self._customer_memories: Dict[str, CustomerMemory] = {}
        
        # Event listeners
        self._event_listeners: Dict[str, List[Callable]] = {}
        
        # Initialize with demo data
        self._initialize_demo_data()
        
        # Load persistent customer memories
        self._load_customer_memories()
    
    def _initialize_demo_data(self):
        """Initialize with demo data for testing."""
        # Demo rooms
        demo_rooms = [
            Room("101", "deluxe", RoomStatus.AVAILABLE, 200.0, 200.0, 1),
            Room("102", "deluxe", RoomStatus.AVAILABLE, 200.0, 200.0, 1),
            Room("201", "suite", RoomStatus.AVAILABLE, 350.0, 350.0, 2),
            Room("202", "standard", RoomStatus.OCCUPIED, 150.0, 150.0, 2),
        ]
        
        for room in demo_rooms:
            self._rooms[room.room_id] = room
        
        # Demo pricing rules
        demo_pricing = [
            PricingRule("standard", 150.0, 1.0, 1.0),
            PricingRule("deluxe", 200.0, 1.2, 1.1),
            PricingRule("suite", 350.0, 1.3, 1.2),
        ]
        
        for rule in demo_pricing:
            self._pricing_rules[rule.room_type] = rule
    
    def add_event_listener(self, event_type: str, callback: Callable):
        """Add event listener for state changes."""
        with self._lock:
            if event_type not in self._event_listeners:
                self._event_listeners[event_type] = []
            self._event_listeners[event_type].append(callback)
    
    def _notify_listeners(self, event_type: str, data: Any):
        """Notify all listeners of an event."""
        if event_type in self._event_listeners:
            for callback in self._event_listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in event listener: {e}")
    
    # Guest Profile methods
    def get_guest_profile(self, guest_id: str) -> Optional[GuestProfile]:
        """Get guest profile by ID."""
        with self._lock:
            return self._guest_profiles.get(guest_id)
    
    def create_guest_profile(self, profile: GuestProfile) -> GuestProfile:
        """Create new guest profile."""
        with self._lock:
            self._guest_profiles[profile.guest_id] = profile
            self._notify_listeners("guest_profile_created", profile)
            return profile
    
    def update_guest_profile(self, guest_id: str, updates: Dict[str, Any]) -> Optional[GuestProfile]:
        """Update guest profile."""
        with self._lock:
            if guest_id in self._guest_profiles:
                profile = self._guest_profiles[guest_id]
                for key, value in updates.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)
                self._notify_listeners("guest_profile_updated", profile)
                return profile
            return None
    
    # Room methods
    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID."""
        with self._lock:
            return self._rooms.get(room_id)
    
    def get_available_rooms(self, room_type: Optional[str] = None) -> List[Room]:
        """Get available rooms, optionally filtered by type."""
        with self._lock:
            rooms = [room for room in self._rooms.values() 
                    if room.status == RoomStatus.AVAILABLE]
            if room_type:
                rooms = [room for room in rooms if room.room_type == room_type]
            return rooms
    
    def update_room_status(self, room_id: str, status: RoomStatus) -> Optional[Room]:
        """Update room status."""
        with self._lock:
            if room_id in self._rooms:
                room = self._rooms[room_id]
                old_status = room.status
                room.status = status
                room.last_updated = datetime.now()
                self._notify_listeners("room_status_changed", {
                    "room_id": room_id,
                    "old_status": old_status,
                    "new_status": status
                })
                return room
            return None
    
    # Booking methods
    def get_booking(self, booking_id: str) -> Optional[Booking]:
        """Get booking by ID."""
        with self._lock:
            return self._bookings.get(booking_id)
    
    def create_booking(self, booking: Booking) -> Booking:
        """Create new booking."""
        with self._lock:
            self._bookings[booking.booking_id] = booking
            self._notify_listeners("booking_created", booking)
            return booking
    
    def update_booking_status(self, booking_id: str, status: BookingStatus) -> Optional[Booking]:
        """Update booking status."""
        with self._lock:
            if booking_id in self._bookings:
                booking = self._bookings[booking_id]
                booking.status = status
                self._notify_listeners("booking_status_updated", booking)
                return booking
            return None
    
    # Task methods
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        with self._lock:
            return self._tasks.get(task_id)
    
    def create_task(self, task: Task) -> Task:
        """Create new task."""
        with self._lock:
            self._tasks[task.task_id] = task
            self._notify_listeners("task_created", task)
            return task
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[Task]:
        """Update task status."""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = status
                if status == TaskStatus.COMPLETED:
                    task.completed_at = datetime.now()
                self._notify_listeners("task_status_updated", task)
                return task
            return None
    
    # Pricing methods
    def get_pricing_rule(self, room_type: str) -> Optional[PricingRule]:
        """Get pricing rule for room type."""
        with self._lock:
            return self._pricing_rules.get(room_type)
    
    def update_pricing_rule(self, room_type: str, updates: Dict[str, Any]) -> Optional[PricingRule]:
        """Update pricing rule."""
        with self._lock:
            if room_type in self._pricing_rules:
                rule = self._pricing_rules[room_type]
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                rule.last_updated = datetime.now()
                self._notify_listeners("pricing_rule_updated", rule)
                return rule
            return None
    
    # Utility methods
    def get_system_state(self) -> Dict[str, Any]:
        """Get complete system state for debugging."""
        with self._lock:
            return {
                "guests": len(self._guest_profiles),
                "rooms": len(self._rooms),
                "bookings": len(self._bookings),
                "tasks": len(self._tasks),
                "pricing_rules": len(self._pricing_rules),
                "available_rooms": len([r for r in self._rooms.values() 
                                       if r.status == RoomStatus.AVAILABLE]),
                "pending_tasks": len([t for t in self._tasks.values() 
                                    if t.status == TaskStatus.PENDING])
            }

    def _load_customer_memories(self):
        """Load customer memories from persistent storage."""
        try:
            # For demo, use JSON file storage
            memory_file = os.path.join(os.path.dirname(__file__), "..", "data", "customer_memories.json")

            if os.path.exists(memory_file):
                with open(memory_file, "r") as f:
                    memories_data = json.load(f)
                    for customer_id, memory_data in memories_data.items():
                        memory = CustomerMemory(**memory_data)
                        self._customer_memories[customer_id] = memory
                        logger.debug(f"Loaded customer memory for {customer_id}")
        except Exception as e:
            logger.error(f"Error loading customer memories: {e}")
    
    def _save_customer_memories(self):
        """Save customer memories to persistent storage."""
        try:
            # For demo, use JSON file storage
            memory_file = os.path.join(os.path.dirname(__file__), "..", "data", "customer_memories.json")
            
            # Convert memories to dict for JSON serialization
            memories_dict = {}
            for customer_id, memory in self._customer_memories.items():
                memories_dict[customer_id] = {
                    "customer_id": memory.customer_id,
                    "personal_info": memory.personal_info,
                    "preferences": memory.preferences,
                    "stay_history": memory.stay_history,
                    "service_requests": memory.service_requests,
                    "complaint_history": memory.complaint_history,
                    "loyalty_info": memory.loyalty_info,
                    "last_updated": memory.last_updated.isoformat()
                }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(memory_file), exist_ok=True)
            
            with open(memory_file, "w") as f:
                json.dump(memories_dict, f, indent=2)
                logger.debug(f"Saved {len(memories_dict)} customer memories")
        except Exception as e:
            logger.error(f"Error saving customer memories: {e}")

    # Customer Memory methods
    def get_customer_memory(self, customer_id: str) -> Optional[CustomerMemory]:
        """Get customer memory by ID."""
        with self._lock:
            return self._customer_memories.get(customer_id)
    
    def create_customer_memory(self, memory: CustomerMemory) -> CustomerMemory:
        """Create new customer memory."""
        with self._lock:
            self._customer_memories[memory.customer_id] = memory
            memory.last_updated = datetime.now()
            self._save_customer_memories()
            self._notify_listeners("customer_memory_created", memory)
            return memory

    def update_customer_memory(self, customer_id: str, updates: Dict[str, Any]) -> Optional[CustomerMemory]:
        """Update customer memory."""
        with self._lock:
            if customer_id in self._customer_memories:
                memory = self._customer_memories[customer_id]
                for key, value in updates.items():
                    if hasattr(memory, key):
                        setattr(memory, key, value)
                memory.last_updated = datetime.now()
                self._save_customer_memories()
                self._notify_listeners("customer_memory_updated", memory)
                return memory
            return None
    
    def add_stay_to_history(self, customer_id: str, stay_info: Dict[str, Any]) -> None:
        """Add stay information to customer history."""
        with self._lock:
            if customer_id in self._customer_memories:
                memory = self._customer_memories[customer_id]
                memory.stay_history.append(stay_info)
                memory.last_updated = datetime.now()
                self._save_customer_memories()
                self._notify_listeners("stay_history_updated", memory)
    
    def add_service_request(self, customer_id: str, service_info: Dict[str, Any]) -> None:
        """Add service request to customer history."""
        with self._lock:
            if customer_id in self._customer_memories:
                memory = self._customer_memories[customer_id]
                memory.service_requests.append(service_info)
                memory.last_updated = datetime.now()
                self._save_customer_memories()
                self._notify_listeners("service_request_added", memory)
    
    def add_complaint(self, customer_id: str, complaint_info: Dict[str, Any]) -> None:
        """Add complaint to customer history."""
        with self._lock:
            if customer_id in self._customer_memories:
                memory = self._customer_memories[customer_id]
                memory.complaint_history.append(complaint_info)
                memory.last_updated = datetime.now()
                self._save_customer_memories()
                self._notify_listeners("complaint_history_updated", memory)

# Global state instance
state_layer = StateLayer()
