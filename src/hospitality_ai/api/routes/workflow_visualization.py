"""
Workflow Visualization API Routes
Provides real-time visualization of agent interactions and workflow flows
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict, List, Any
import json
import asyncio
from datetime import datetime

from hospitality_ai.monitoring.workflow_monitor import workflow_monitor

router = APIRouter(prefix="/workflow", tags=["workflow"])

# Store active WebSocket connections
active_connections: List[WebSocket] = []

@router.get("/dashboard", response_class=HTMLResponse)
async def get_workflow_dashboard():
    """Serve the workflow visualization dashboard"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Workflow Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.6/dist/vis-network.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        #workflow-graph {
            height: 600px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        .agent-node {
            font-size: 12px;
        }
        
        .human-node {
            background-color: #fbbf24 !important;
            border: 2px solid #f59e0b !important;
        }
        
        .agent-guest {
            background-color: #60a5fa !important;
            border: 2px solid #3b82f6 !important;
        }
        
        .agent-orchestrator {
            background-color: #a78bfa !important;
            border: 2px solid #8b5cf6 !important;
        }
        
        .agent-booking {
            background-color: #34d399 !important;
            border: 2px solid #10b981 !important;
        }
        
        .agent-operations {
            background-color: #f87171 !important;
            border: 2px solid #ef4444 !important;
        }
        
        .agent-decision {
            background-color: #fbbf24 !important;
            border: 2px solid #f59e0b !important;
        }
        
        .agent-revenue {
            background-color: #fb923c !important;
            border: 2px solid #f97316 !important;
        }
        
        .event-log {
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto p-6">
        <h1 class="text-3xl font-bold text-gray-800 mb-6">Agent Workflow Visualization</h1>
        
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <!-- Main Graph -->
            <div class="lg:col-span-3">
                <div class="bg-white rounded-lg shadow-lg p-4">
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-xl font-semibold text-gray-700">Agent Interaction Flow</h2>
                        <div class="flex space-x-2">
                            <button onclick="clearGraph()" class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm">
                                Clear
                            </button>
                            <button onclick="toggleAutoLayout()" class="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm">
                                Auto Layout
                            </button>
                        </div>
                    </div>
                    <div id="workflow-graph"></div>
                </div>
            </div>
            
            <!-- Side Panel -->
            <div class="space-y-4">
                <!-- Legend -->
                <div class="bg-white rounded-lg shadow-lg p-4">
                    <h3 class="text-lg font-semibold text-gray-700 mb-3">Legend</h3>
                    <div class="space-y-2 text-sm">
                        <div class="flex items-center space-x-2">
                            <div class="w-4 h-4 bg-yellow-400 rounded"></div>
                            <span>Human/Guest</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-4 h-4 bg-blue-400 rounded"></div>
                            <span>Guest Agent</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-4 h-4 bg-purple-400 rounded"></div>
                            <span>Orchestrator</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-4 h-4 bg-green-400 rounded"></div>
                            <span>Booking Agent</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-4 h-4 bg-red-400 rounded"></div>
                            <span>Operations Agent</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-4 h-4 bg-yellow-500 rounded"></div>
                            <span>Decision Agent</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <div class="w-4 h-4 bg-orange-400 rounded"></div>
                            <span>Revenue Agent</span>
                        </div>
                    </div>
                </div>
                
                <!-- Stats -->
                <div class="bg-white rounded-lg shadow-lg p-4">
                    <h3 class="text-lg font-semibold text-gray-700 mb-3">Live Stats</h3>
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between">
                            <span>Total Events:</span>
                            <span id="total-events" class="font-semibold">0</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Active Agents:</span>
                            <span id="active-agents" class="font-semibold">0</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Tool Calls:</span>
                            <span id="tool-calls" class="font-semibold">0</span>
                        </div>
                    </div>
                </div>
                
                <!-- Event Log -->
                <div class="bg-white rounded-lg shadow-lg p-4">
                    <h3 class="text-lg font-semibold text-gray-700 mb-3">Event Log</h3>
                    <div id="event-log" class="event-log space-y-1">
                        <div class="text-gray-500">Waiting for events...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Graph setup
        let nodes = null;
        let edges = null;
        let network = null;
        let autoLayout = true;
        
        // Agent positions for layout
        const agentPositions = {
            'guest': { x: 100, y: 300 },
            'guest_agent': { x: 300, y: 300 },
            'orchestrator': { x: 500, y: 300 },
            'booking_agent': { x: 700, y: 200 },
            'operations_agent': { x: 700, y: 300 },
            'decision_agent': { x: 700, y: 400 },
            'revenue_agent': { x: 900, y: 300 }
        };
        
        function initializeGraph() {
            nodes = new vis.DataSet([
                { id: 'guest', label: 'Guest/Human', group: 'human', ...agentPositions.guest },
                { id: 'guest_agent', label: 'Guest Agent', group: 'agent-guest', ...agentPositions.guest_agent },
                { id: 'orchestrator', label: 'Orchestrator', group: 'agent-orchestrator', ...agentPositions.orchestrator },
                { id: 'booking_agent', label: 'Booking Agent', group: 'agent-booking', ...agentPositions.booking_agent },
                { id: 'operations_agent', label: 'Operations Agent', group: 'agent-operations', ...agentPositions.operations_agent },
                { id: 'decision_agent', label: 'Decision Agent', group: 'agent-decision', ...agentPositions.decision_agent },
                { id: 'revenue_agent', label: 'Revenue Agent', group: 'agent-revenue', ...agentPositions.revenue_agent }
            ]);
            
            edges = new vis.DataSet([]);
            
            const container = document.getElementById('workflow-graph');
            const data = { nodes: nodes, edges: edges };
            
            const options = {
                nodes: {
                    shape: 'dot',
                    size: 20,
                    font: {
                        size: 12,
                        color: '#ffffff'
                    },
                    borderWidth: 2
                },
                edges: {
                    arrows: 'to',
                    smooth: {
                        type: 'curvedCW',
                        roundness: 0.2
                    },
                    width: 2,
                    color: {
                        color: '#848484',
                        highlight: '#2b7ce9'
                    }
                },
                groups: {
                    human: { color: '#fbbf24' },
                    'agent-guest': { color: '#60a5fa' },
                    'agent-orchestrator': { color: '#a78bfa' },
                    'agent-booking': { color: '#34d399' },
                    'agent-operations': { color: '#f87171' },
                    'agent-decision': { color: '#fbbf24' },
                    'agent-revenue': { color: '#fb923c' }
                },
                physics: {
                    enabled: false
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200
                }
            };
            
            network = new vis.Network(container, data, options);
        }
        
        function addInteraction(fromAgent, toAgent, action, details = "") {
            const edgeId = `${fromAgent}-${toAgent}-${Date.now()}`;
            const label = action + (details ? `: ${details}` : "");
            
            edges.add({
                id: edgeId,
                from: fromAgent,
                to: toAgent,
                label: label,
                font: { size: 10, align: 'middle' },
                color: { color: '#2b7ce9' }
            });
            
            // Pulse the target node
            const targetNode = nodes.get(toAgent);
            if (targetNode) {
                nodes.update({
                    id: toAgent,
                    borderWidth: 4,
                    color: { highlight: { background: '#ef4444' } }
                });
                
                setTimeout(() => {
                    nodes.update({
                        id: toAgent,
                        borderWidth: 2
                    });
                }, 1000);
            }
            
            // Auto-remove old edges to keep graph clean
            if (edges.length > 20) {
                const oldEdges = edges.getIds().slice(0, 10);
                edges.remove(oldEdges);
            }
        }
        
        function updateStats(stats) {
            document.getElementById('total-events').textContent = stats.total_events || 0;
            document.getElementById('active-agents').textContent = Object.keys(stats.active_tools || {}).length || 0;
            document.getElementById('tool-calls').textContent = Object.values(stats.active_tools || {}).reduce((sum, count) => sum + count.count, 0) || 0;
        }
        
        function addEventLog(message) {
            const log = document.getElementById('event-log');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.className = 'text-xs text-gray-600 border-b border-gray-100 pb-1';
            logEntry.innerHTML = `<span class="text-gray-400">[${timestamp}]</span> ${message}`;
            
            log.insertBefore(logEntry, log.firstChild);
            
            // Keep only last 50 entries
            while (log.children.length > 50) {
                log.removeChild(log.lastChild);
            }
        }
        
        function clearGraph() {
            edges.clear();
            document.getElementById('event-log').innerHTML = '<div class="text-gray-500">Graph cleared...</div>';
        }
        
        function toggleAutoLayout() {
            autoLayout = !autoLayout;
            const options = { physics: { enabled: autoLayout } };
            network.setOptions(options);
        }
        
        // WebSocket connection for real-time updates
        const ws = new WebSocket('ws://localhost:8000/workflow/ws');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'workflow_event') {
                const { from, to, action, details } = data.payload;
                addInteraction(from, to, action, details);
                addEventLog(`${from} → ${to}: ${action}`);
            } else if (data.type === 'workflow_stats') {
                updateStats(data.payload);
            }
        };
        
        ws.onopen = function() {
            addEventLog('Connected to workflow stream');
        };
        
        ws.onclose = function() {
            addEventLog('Disconnected from workflow stream');
            // Try to reconnect after 3 seconds
            setTimeout(() => location.reload(), 3000);
        };
        
        // Initialize graph on page load
        document.addEventListener('DOMContentLoaded', function() {
            initializeGraph();
            addEventLog('Workflow visualization initialized');
        });
    </script>
</body>
</html>
    """

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time workflow updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial stats
        initial_stats = workflow_monitor.get_workflow_summary()
        await websocket.send_text(json.dumps({
            "type": "workflow_stats",
            "payload": initial_stats
        }))
        
        # Keep connection alive and send updates
        while True:
            await asyncio.sleep(1)  # Check every second
            
            # Get latest stats
            current_stats = workflow_monitor.get_workflow_summary()
            
            # Check for new events and send them
            if len(workflow_monitor.workflow_events) > initial_stats.get("total_events", 0):
                # Send new events
                for event in workflow_monitor.workflow_events[-5:]:  # Last 5 events
                    if "tool" in event:
                        await websocket.send_text(json.dumps({
                            "type": "workflow_event",
                            "payload": {
                                "from": event.get("from", "unknown"),
                                "to": event.get("tool", "unknown"),
                                "action": event.get("event_type", "unknown"),
                                "details": event.get("details", "")
                            }
                        }))
                
                # Update stats
                await websocket.send_text(json.dumps({
                    "type": "workflow_stats", 
                    "payload": current_stats
                }))
                
                initial_stats = current_stats
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@router.get("/stats")
async def get_workflow_stats():
    """Get current workflow statistics"""
    return workflow_monitor.get_workflow_summary()

@router.post("/simulate-event")
async def simulate_workflow_event(event: Dict[str, Any]):
    """Simulate a workflow event for testing"""
    workflow_monitor.workflow_events.append({
        "timestamp": datetime.now().isoformat(),
        "event_type": event.get("event_type", "test"),
        "from": event.get("from", "test_agent"),
        "to": event.get("to", "test_target"),
        "tool": event.get("tool", "test_tool"),
        "details": event.get("details", "Test event")
    })
    
    # Broadcast to all connected clients
    for connection in active_connections:
        try:
            await connection.send_text(json.dumps({
                "type": "workflow_event",
                "payload": event
            }))
        except:
            pass
    
    return {"status": "event added"}