"""
Revenue Agent - Handles pricing optimization, demand prediction, and strategy.

Solves:
R1: Pricing optimization
R2: Demand prediction
R3: Strategy

Dependencies:
- State Layer (occupancy, bookings)
- Optional external market data
- Existing CrewAI agents (via integration bridges)

Does NOT talk to guests directly - internal optimization only.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import logging
from datetime import datetime, timedelta

from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..domain.state_layer import state_layer
from ..config.settings import Settings
from ..monitoring.workflow_monitor import workflow_monitor

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class PricingRequest:
    """Pricing optimization request data model."""
    room_type: str
    check_in: str
    check_out: str
    current_price: Optional[float] = None
    competitor_data: Optional[List[Dict[str, Any]]] = None
    optimization_goal: str = "maximize_revenue"


@dataclass
class DemandAnalysisRequest:
    """Demand prediction request data model."""
    room_type: str
    date_range: str
    historical_days: int = 30
    factors: Optional[List[str]] = None


@dataclass
class RevenueResponse:
    """Revenue operation response data model."""
    success: bool
    message: str
    recommendation_id: Optional[str] = None
    optimized_price: Optional[float] = None
    demand_forecast: Optional[Dict[str, Any]] = None
    strategy: Optional[Dict[str, Any]] = None
    action_taken: str = "revenue_operation_completed"


# CrewAI Agent Bridge Classes
class PricingInsightBridge:
    """Bridge to existing PricingInsightAgent without modification."""
    
    def __init__(self):
        try:
            from ..agents.pricing_insight_agent import PricingInsightAgent
            from ..application.pricing_insight_service import PricingInsightService
            
            self._service = PricingInsightService()
            self._agent = PricingInsightAgent(self._service)
        except ImportError:
            self._agent = None
            self._service = None
    
    def call_agent(self) -> Optional[Dict[str, Any]]:
        """Call existing CrewAI agent and return results."""
        if self._agent is None:
            return {"error": "PricingInsightAgent not available"}
        
        try:
            result = self._agent.run()
            return result
        except Exception as e:
            return {"error": str(e)}


class StrategyRecommendationBridge:
    """Bridge to existing StrategyRecommendationAgent without modification."""
    
    def __init__(self):
        try:
            from ..agents.strategy_recommendation_agent import StrategyRecommendationAgent
            from ..application.recommendation_service import RecommendationService
            
            self._service = RecommendationService()
            self._agent = StrategyRecommendationAgent(self._service)
        except ImportError:
            self._agent = None
            self._service = None
    
    def call_agent(self, pricing_report: Dict[str, Any], monitoring_report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call existing CrewAI agent with reports."""
        if self._agent is None:
            return {"error": "StrategyRecommendationAgent not available"}
        
        try:
            # Convert dict to expected report objects if needed
            result = self._agent.run(
                pricing_report=pricing_report,
                monitoring_report=monitoring_report
            )
            return result
        except Exception as e:
            return {"error": str(e)}


class PerformanceMonitoringBridge:
    """Bridge to existing PerformanceMonitoringAgent without modification."""
    
    def __init__(self):
        try:
            from ..agents.performance_monitoring_agent import PerformanceMonitoringAgent
            from ..application.performance_monitoring_service import PerformanceMonitoringService
            
            self._service = PerformanceMonitoringService()
            self._agent = PerformanceMonitoringAgent(self._service)
        except ImportError:
            self._agent = None
            self._service = None
    
    def call_agent(self) -> Optional[Dict[str, Any]]:
        """Call existing CrewAI agent and return results."""
        if self._agent is None:
            return {"error": "PerformanceMonitoringAgent not available"}
        
        try:
            result = self._agent.run()
            return result
        except Exception as e:
            return {"error": str(e)}


# Standalone tool functions for LangChain
@tool
def optimize_pricing_tool(room_type: str, current_price: float, competitor_data: Optional[List[Dict[str, Any]]] = None, optimization_goal: str = "maximize_revenue") -> str:
    """Optimize pricing using existing pricing insights and State Layer data."""
    try:
        # Get pricing insights from existing CrewAI agent
        pricing_bridge = PricingInsightBridge()
        pricing_insights = pricing_bridge.call_agent()
        
        if pricing_insights and "error" not in pricing_insights:
            # Extract pricing recommendations from existing agent
            insights = pricing_insights.get("insights", {})
            recommendations = pricing_insights.get("recommendations", {})
            
            optimization_result = {
                "room_type": room_type,
                "current_price": current_price,
                "competitor_data": competitor_data,
                "optimization_goal": optimization_goal,
                "existing_insights": insights,
                "recommendations": recommendations,
                "optimized_price": _calculate_optimized_price(current_price, insights, competitor_data),
                "optimization_confidence": _calculate_confidence(insights, competitor_data),
                "optimization_timestamp": datetime.now().isoformat()
            }
        else:
            # Fallback to basic optimization if CrewAI agent unavailable
            optimization_result = {
                "room_type": room_type,
                "current_price": current_price,
                "competitor_data": competitor_data,
                "optimization_goal": optimization_goal,
                "optimized_price": _basic_price_optimization(current_price, competitor_data),
                "optimization_confidence": 0.7,
                "fallback_used": True,
                "optimization_timestamp": datetime.now().isoformat()
            }
        
        return json.dumps({
            "optimization_id": f"OPT{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "optimization_result": optimization_result,
            "message": "Pricing optimization completed"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def predict_demand_tool(room_type: str, date_range: str, historical_days: int = 30, factors: Optional[List[str]] = None) -> str:
    """Predict demand using State Layer booking data and external factors."""
    try:
        # Get historical booking data from State Layer
        bookings = state_layer._bookings  # Access internal storage
        rooms = state_layer._rooms  # Access internal storage
        
        # Analyze historical occupancy for room type
        historical_data = _analyze_historical_occupancy(bookings, rooms, room_type, historical_days)
        
        # Get performance monitoring insights
        monitoring_bridge = PerformanceMonitoringBridge()
        monitoring_data = monitoring_bridge.call_agent()
        
        # Predict demand based on patterns and external factors
        demand_forecast = {
            "room_type": room_type,
            "date_range": date_range,
            "historical_days_analyzed": historical_days,
            "historical_occupancy": historical_data,
            "monitoring_insights": monitoring_data,
            "factors_considered": factors or ["occupancy", "seasonality", "day_of_week"],
            "predicted_demand": _calculate_demand_prediction(historical_data, factors),
            "demand_confidence": _calculate_demand_confidence(historical_data),
            "forecast_timestamp": datetime.now().isoformat()
        }
        
        return json.dumps({
            "forecast_id": f"DF{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "demand_forecast": demand_forecast,
            "message": "Demand prediction completed"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def generate_strategy_tool(pricing_insights: Dict[str, Any], demand_forecast: Dict[str, Any], monitoring_data: Optional[Dict[str, Any]] = None) -> str:
    """Generate revenue strategy using existing strategy recommendations."""
    try:
        # Use existing StrategyRecommendationAgent
        strategy_bridge = StrategyRecommendationBridge()
        
        # Prepare data for existing agent
        strategy_result = strategy_bridge.call_agent(
            pricing_report=pricing_insights,
            monitoring_report=monitoring_data or {}
        )
        
        if strategy_result and "error" not in strategy_result:
            # Enhance with demand forecast
            enhanced_strategy = {
                "base_strategy": strategy_result,
                "demand_forecast": demand_forecast,
                "pricing_insights": pricing_insights,
                "monitoring_data": monitoring_data,
                "strategic_recommendations": _enhance_strategy_with_demand(
                    strategy_result, demand_forecast
                ),
                "strategy_timestamp": datetime.now().isoformat()
            }
        else:
            # Fallback strategy if CrewAI agent unavailable
            enhanced_strategy = {
                "fallback_strategy": _generate_fallback_strategy(pricing_insights, demand_forecast),
                "demand_forecast": demand_forecast,
                "pricing_insights": pricing_insights,
                "monitoring_data": monitoring_data,
                "fallback_used": True,
                "strategy_timestamp": datetime.now().isoformat()
            }
        
        return json.dumps({
            "strategy_id": f"ST{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "strategy_result": enhanced_strategy,
            "message": "Revenue strategy generated"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def analyze_competitor_pricing_tool(competitor_data: List[Dict[str, Any]], room_type: str) -> str:
    """Analyze competitor pricing data for positioning insights."""
    try:
        analysis_result = {
            "room_type": room_type,
            "competitor_count": len(competitor_data),
            "competitor_analysis": _analyze_competitors(competitor_data),
            "market_positioning": _determine_market_positioning(competitor_data),
            "price_gaps": _calculate_price_gaps(competitor_data),
            "recommendations": _generate_competitor_recommendations(competitor_data),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return json.dumps({
            "analysis_id": f"CP{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "analysis_result": analysis_result,
            "message": "Competitor pricing analysis completed"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# Helper functions for revenue optimization
def _calculate_optimized_price(current_price: float, insights: Dict[str, Any], competitor_data: Optional[List[Dict[str, Any]]]) -> float:
    """Calculate optimized price based on insights and competitor data."""
    # Extract recommendations from existing pricing insights
    recommended_price = insights.get("recommended_price", current_price)
    
    if competitor_data:
        # Consider competitor positioning
        avg_competitor_price = sum(c.get("price", 0) for c in competitor_data) / len(competitor_data)
        
        # Weight current price, recommendation, and competitor average
        optimized_price = (current_price * 0.4 + recommended_price * 0.4 + avg_competitor_price * 0.2)
    else:
        optimized_price = (current_price * 0.6 + recommended_price * 0.4)
    
    return round(optimized_price, 2)


def _calculate_confidence(insights: Dict[str, Any], competitor_data: Optional[List[Dict[str, Any]]]) -> float:
    """Calculate confidence level for optimization."""
    base_confidence = 0.8  # Base confidence from existing insights
    
    if competitor_data and len(competitor_data) >= 3:
        base_confidence += 0.1  # More confidence with more competitors
    
    return min(base_confidence, 1.0)


def _basic_price_optimization(current_price: float, competitor_data: Optional[List[Dict[str, Any]]]) -> float:
    """Basic price optimization when CrewAI agent unavailable."""
    if competitor_data:
        # Simple competitor-based optimization
        avg_competitor_price = sum(c.get("price", 0) for c in competitor_data) / len(competitor_data)
        
        # Position slightly above average if current price is low
        if current_price < avg_competitor_price * 0.9:
            return avg_competitor_price * 0.95
        elif current_price > avg_competitor_price * 1.1:
            return avg_competitor_price * 1.05
        else:
            return current_price
    
    return current_price


def _analyze_historical_occupancy(bookings: List, rooms: List, room_type: str, days: int) -> Dict[str, Any]:
    """Analyze historical occupancy data."""
    # Simplified historical analysis
    total_rooms = len([r for r in rooms if r.room_type == room_type])
    if total_rooms == 0:
        return {"error": "No rooms found for type"}
    
    return {
        "room_type": room_type,
        "total_rooms": total_rooms,
        "historical_days": days,
        "average_occupancy": 0.75,  # Placeholder
        "occupancy_trend": "stable",
        "peak_days": ["friday", "saturday"],
        "low_days": ["tuesday", "wednesday"]
    }


def _calculate_demand_prediction(historical_data: Dict[str, Any], factors: Optional[List[str]]) -> Dict[str, Any]:
    """Calculate demand prediction from historical data."""
    base_demand = historical_data.get("average_occupancy", 0.75)
    
    # Apply factors
    if factors:
        if "seasonality" in factors:
            base_demand *= 1.1  # Seasonal adjustment
        if "day_of_week" in factors:
            base_demand *= 0.95  # Weekday adjustment
    
    return {
        "predicted_occupancy": min(base_demand, 1.0),
        "demand_level": "high" if base_demand > 0.8 else "medium" if base_demand > 0.6 else "low",
        "revenue_potential": "high" if base_demand > 0.8 else "medium"
    }


def _calculate_demand_confidence(historical_data: Dict[str, Any]) -> float:
    """Calculate confidence level for demand prediction."""
    days_analyzed = historical_data.get("historical_days", 30)
    
    if days_analyzed >= 60:
        return 0.9
    elif days_analyzed >= 30:
        return 0.8
    else:
        return 0.6


def _enhance_strategy_with_demand(strategy_result: Dict[str, Any], demand_forecast: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance strategy with demand forecast insights."""
    base_recommendations = strategy_result.get("recommendations", [])
    demand_level = demand_forecast.get("predicted_demand", {}).get("demand_level", "medium")
    
    # Add demand-specific recommendations
    if demand_level == "high":
        base_recommendations.append("Increase prices by 5-10% during high demand periods")
    elif demand_level == "low":
        base_recommendations.append("Consider special offers or discounts during low demand")
    
    return base_recommendations


def _generate_fallback_strategy(pricing_insights: Dict[str, Any], demand_forecast: Dict[str, Any]) -> Dict[str, Any]:
    """Generate fallback strategy when CrewAI agent unavailable."""
    return {
        "recommendations": [
            "Monitor competitor pricing regularly",
            "Adjust prices based on occupancy patterns",
            "Consider seasonal demand variations"
        ],
        "priority_actions": [
            "Review pricing weekly",
            "Analyze competitor positioning",
            "Monitor booking trends"
        ]
    }


def _analyze_competitors(competitor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze competitor pricing patterns."""
    prices = [c.get("price", 0) for c in competitor_data]
    
    return {
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "avg_price": sum(prices) / len(prices) if prices else 0,
        "price_variance": max(prices) - min(prices) if prices else 0,
        "competitor_count": len(competitor_data)
    }


def _determine_market_positioning(competitor_data: List[Dict[str, Any]]) -> str:
    """Determine market positioning relative to competitors."""
    if not competitor_data:
        return "no_competitor_data"
    
    prices = [c.get("price", 0) for c in competitor_data]
    avg_price = sum(prices) / len(prices)
    
    # This would use our hotel's price in real implementation
    # For now, return general positioning
    return "competitive"  # Placeholder


def _calculate_price_gaps(competitor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate price gaps between competitors."""
    if len(competitor_data) < 2:
        return {"message": "Insufficient competitor data"}
    
    prices = sorted([c.get("price", 0) for c in competitor_data])
    
    return {
        "min_max_gap": prices[-1] - prices[0],
        "avg_gap": sum(prices) / len(prices) - prices[0],
        "price_spread": (prices[-1] - prices[0]) / prices[0] * 100 if prices[0] > 0 else 0
    }


def _generate_competitor_recommendations(competitor_data: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on competitor analysis."""
    recommendations = []
    
    if len(competitor_data) >= 3:
        recommendations.append("Good competitor coverage for market analysis")
    else:
        recommendations.append("Consider monitoring more competitors")
    
    recommendations.append("Regular competitor price monitoring is essential")
    recommendations.append("Position based on value, not just price")
    
    return recommendations


class RevenueAgent:
    """
    LLM-powered Revenue Agent using LangChain.
    
    Handles pricing optimization, demand prediction, and strategy generation.
    Integrates with existing CrewAI agents without modification.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        
        # Configure LLM from environment variables
        if llm:
            self.llm = llm
        else:
            self.llm = self._create_llm()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance from environment configuration."""
        logger.debug(f"Creating Revenue Agent LLM with model: {self.settings.llm_model}")
        logger.debug(f"Base URL: {self.settings.llm_base_url}")
        logger.debug(f"Temperature: {self.settings.llm_temperature}")
        logger.debug(f"Max tokens: {self.settings.llm_max_tokens}")
        
        return ChatOpenAI(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            temperature=self.settings.llm_temperature,  # Revenue Agent uses 0.3
            max_tokens=self.settings.llm_max_tokens,
            timeout=self.settings.llm_timeout_seconds,
            tool_choice="auto"  # Fix tool choice error for vLLM compatibility
        )
    
    def _create_agent(self):
        """Create LangChain agent with tools."""
        self.state_layer = state_layer
        
        # Initialize CrewAI bridges
        self.pricing_bridge = PricingInsightBridge()
        self.strategy_bridge = StrategyRecommendationBridge()
        self.monitoring_bridge = PerformanceMonitoringBridge()
        
        tools = [
            optimize_pricing_tool,
            predict_demand_tool,
            generate_strategy_tool,
            analyze_competitor_pricing_tool
        ]
        
        system_prompt = """
        You are a Revenue Agent for a hospitality AI system. Your roles:
        
        1. Pricing optimization (R1) - Optimize room prices for maximum revenue
        2. Demand prediction (R2) - Forecast demand based on historical data
        3. Strategy (R3) - Generate revenue management strategies
        
        Available tools:
        - optimize_pricing_tool: Optimize pricing using insights and competitor data
        - predict_demand_tool: Predict demand using historical booking data
        - generate_strategy_tool: Generate revenue strategies with existing agents
        - analyze_competitor_pricing_tool: Analyze competitor pricing for positioning
        
        Integration capabilities:
        - Uses existing PricingInsightAgent for pricing analysis
        - Uses existing StrategyRecommendationAgent for strategy generation
        - Uses existing PerformanceMonitoringAgent for system health
        - Integrates with State Layer for booking and occupancy data
        
        Rules:
        - Do NOT talk to guests directly
        - Focus on revenue optimization and strategy
        - Leverage existing agent insights when available
        - Provide data-driven recommendations
        - Consider market positioning and demand patterns
        
        Be analytical, data-driven, and strategic in your recommendations.
        """
        
        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )
    
    def optimize_pricing(self, request: PricingRequest) -> RevenueResponse:
        """
        Optimize pricing for specific room and dates.
        
        Args:
            request: Pricing optimization request with details
            
        Returns:
            RevenueResponse with optimized pricing and recommendations
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are optimizing pricing for revenue maximization.
                
                Room Type: {request.room_type}
                Check-in: {request.check_in}
                Check-out: {request.check_out}
                Current Price: {request.current_price}
                Competitor Data: {request.competitor_data}
                Optimization Goal: {request.optimization_goal}
                
                Use tools to:
                1. Analyze competitor pricing data
                2. Optimize price using existing insights
                3. Consider demand patterns
                4. Provide confidence levels
                5. Generate actionable recommendations
                
                Leverage existing CrewAI agents when available for insights.
                """),
                HumanMessage(content=f"Optimize pricing: {request}")
            ]
            
            # Execute agent
            result = self.agent.invoke({"messages": messages}, config={"callbacks": [workflow_monitor]})
            
            # Extract response
            # Extract response from messages array (modern LangChain format)
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    output = last_message['content']
                else:
                    output = str(last_message)
            else:
                # Fallback for older format or unexpected structure
                output = result.get("output", "Pricing optimization failed")
            
            # Parse result for response
            if "optimized_price" in output.lower():
                return RevenueResponse(
                    success=True,
                    message=output,
                    action_taken="pricing_optimized"
                )
            elif "error" in output.lower():
                return RevenueResponse(
                    success=False,
                    message=output,
                    action_taken="optimization_failed"
                )
            else:
                return RevenueResponse(
                    success=True,
                    message=output,
                    action_taken="pricing_analyzed"
                )
                
        except Exception as e:
            return RevenueResponse(
                success=False,
                message=f"Revenue optimization error: {str(e)}",
                action_taken="optimization_error"
            )
    
    def predict_demand(self, request: DemandAnalysisRequest) -> RevenueResponse:
        """
        Predict demand for room type and date range.
        
        Args:
            request: Demand analysis request with parameters
            
        Returns:
            RevenueResponse with demand forecast and insights
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are predicting demand for revenue planning.
                
                Room Type: {request.room_type}
                Date Range: {request.date_range}
                Historical Days: {request.historical_days}
                Factors: {request.factors}
                
                Use tools to:
                1. Analyze historical booking data from State Layer
                2. Consider seasonal patterns and trends
                3. Factor in external influences
                4. Generate demand forecast
                5. Provide confidence levels
                
                Use State Layer data and existing monitoring insights.
                """),
                HumanMessage(content=f"Predict demand: {request}")
            ]
            
            # Execute agent
            result = self.agent.invoke({"messages": messages}, config={"callbacks": [workflow_monitor]})
            
            # Extract response
            # Extract response from messages array (modern LangChain format)
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    output = last_message['content']
                else:
                    output = str(last_message)
            else:
                # Fallback for older format or unexpected structure
                output = result.get("output", "Demand prediction failed")
            
            # Parse result for response
            if "predicted_demand" in output.lower():
                return RevenueResponse(
                    success=True,
                    message=output,
                    action_taken="demand_predicted"
                )
            elif "error" in output.lower():
                return RevenueResponse(
                    success=False,
                    message=output,
                    action_taken="prediction_failed"
                )
            else:
                return RevenueResponse(
                    success=True,
                    message=output,
                    action_taken="demand_analyzed"
                )
                
        except Exception as e:
            return RevenueResponse(
                success=False,
                message=f"Demand prediction error: {str(e)}",
                action_taken="prediction_error"
            )
    
    def generate_strategy(self, context: Dict[str, Any]) -> RevenueResponse:
        """
        Generate comprehensive revenue strategy.
        
        Args:
            context: Context including pricing insights, demand forecast, etc.
            
        Returns:
            RevenueResponse with strategy recommendations
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are generating a comprehensive revenue strategy.
                
                Context: {context}
                
                Use tools to:
                1. Leverage existing StrategyRecommendationAgent
                2. Integrate pricing insights and demand forecasts
                3. Consider competitor positioning
                4. Generate actionable strategic recommendations
                5. Prioritize revenue optimization actions
                
                Combine insights from all available sources for comprehensive strategy.
                """),
                HumanMessage(content=f"Generate strategy: {context}")
            ]
            
            # Execute agent
            result = self.agent.invoke({"messages": messages}, config={"callbacks": [workflow_monitor]})
            
            # Extract response
            # Extract response from messages array (modern LangChain format)
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    output = last_message['content']
                else:
                    output = str(last_message)
            else:
                # Fallback for older format or unexpected structure
                output = result.get("output", "Strategy generation failed")
            
            # Parse result for response
            if "strategy" in output.lower():
                return RevenueResponse(
                    success=True,
                    message=output,
                    action_taken="strategy_generated"
                )
            elif "error" in output.lower():
                return RevenueResponse(
                    success=False,
                    message=output,
                    action_taken="strategy_failed"
                )
            else:
                return RevenueResponse(
                    success=True,
                    message=output,
                    action_taken="strategy_analyzed"
                )
                
        except Exception as e:
            return RevenueResponse(
                success=False,
                message=f"Strategy generation error: {str(e)}",
                action_taken="strategy_error"
            )


# Global revenue agent instance
revenue_agent = RevenueAgent()
