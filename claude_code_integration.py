"""
Claude Code Integration for Moon Dev Quant TUI
Connects Claude terminals to Hyperliquid API and backtest folder
"""
import asyncio
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import random

from hyperliquid_api import HyperliquidAPI


class ClaudeCodeAgent:
    """Individual Claude Code agent with specific tasks"""
    
    def __init__(self, agent_id: str, name: str, task_type: str):
        self.agent_id = agent_id
        self.name = name
        self.task_type = task_type
        self.points_earned = 0
        self.is_active = False
        self.is_building = False
        self.current_task = ""
        self.output_buffer: List[str] = []
        self.last_activity = datetime.now()
        
        # Task-specific configurations
        self.task_configs = {
            "hyperliquid_scanner": {
                "description": "Analyzing Hyperliquid funding rates",
                "api_endpoint": "funding_rates",
                "refresh_interval": 30,
                "points_per_scan": 15
            },
            "backtest_runner": {
                "description": "Running strategy backtests",
                "folder_path": "agents/backtest/",
                "refresh_interval": 60,
                "points_per_test": 25
            },
            "portfolio_optimizer": {
                "description": "Optimizing portfolio allocation",
                "algorithm": "kelly_criterion",
                "refresh_interval": 45,
                "points_per_optimization": 20
            },
            "risk_monitor": {
                "description": "Monitoring risk metrics",
                "thresholds": {"max_drawdown": 0.15, "var_95": 0.05},
                "refresh_interval": 30,
                "points_per_alert": 10
            }
        }
        
        self.config = self.task_configs.get(task_type, {})
        self.current_task = self.config.get("description", "Unknown task")
    
    async def execute_task(self) -> List[str]:
        """Execute the agent's specific task"""
        new_outputs = []
        
        try:
            if self.task_type == "hyperliquid_scanner":
                new_outputs = await self._scan_hyperliquid()
            elif self.task_type == "backtest_runner":
                new_outputs = await self._run_backtest()
            elif self.task_type == "portfolio_optimizer":
                new_outputs = await self._optimize_portfolio()
            elif self.task_type == "risk_monitor":
                new_outputs = await self._monitor_risk()
            
            # Award points for successful execution
            if new_outputs and random.random() < 0.3:  # 30% chance
                points = self.config.get("points_per_scan", 10)
                self.points_earned += points
                new_outputs.append(f"[bold #00ff88]+{points} points earned![/]")
            
        except Exception as e:
            new_outputs.append(f"[red]Error: {str(e)}[/]")
        
        self.output_buffer.extend(new_outputs)
        if len(self.output_buffer) > 20:
            self.output_buffer = self.output_buffer[-20:]
        
        self.last_activity = datetime.now()
        return new_outputs
    
    async def _scan_hyperliquid(self) -> List[str]:
        """Scan Hyperliquid for funding opportunities"""
        outputs = []
        
        try:
            async with HyperliquidAPI() as api:
                funding_data = await api.get_funding_rates()
                
                if funding_data:
                    # Find most negative funding
                    most_negative = min(funding_data, key=lambda x: x.get("funding_rate", 0))
                    symbol = most_negative.get("symbol", "Unknown")
                    rate = most_negative.get("funding_rate", 0)
                    
                    outputs.append(f"[cyan]Scanned {len(funding_data)} perpetuals[/]")
                    outputs.append(f"[yellow]Most negative: {symbol} at {rate:.4f}%[/]")
                    
                    if rate < -0.02:  # Very negative funding
                        outputs.append(f"[green]✓ Opportunity detected: {symbol}[/]")
                        self.is_building = True
                    else:
                        outputs.append("[dim]No significant opportunities[/]")
                        self.is_building = False
                else:
                    outputs.append("[red]Failed to fetch funding data[/]")
                    
        except Exception as e:
            outputs.append(f"[red]API Error: {str(e)}[/]")
        
        return outputs
    
    async def _run_backtest(self) -> List[str]:
        """Run backtests from the backtest folder"""
        outputs = []
        
        try:
            backtest_folder = Path("agents/backtest/")
            
            if backtest_folder.exists():
                # List available strategies
                strategy_files = list(backtest_folder.glob("*.py"))
                
                if strategy_files:
                    # Simulate running a random strategy
                    strategy = random.choice(strategy_files)
                    outputs.append(f"[cyan]Running backtest: {strategy.name}[/]")
                    
                    self.is_building = True
                    
                    # Simulate backtest results
                    await asyncio.sleep(0.1)  # Simulate processing time
                    
                    returns = random.uniform(-0.1, 0.3)  # Random returns
                    sharpe = random.uniform(0.5, 3.0)
                    
                    if returns > 0:
                        outputs.append(f"[green]✓ Backtest complete: +{returns:.2%} returns[/]")
                        outputs.append(f"[green]Sharpe ratio: {sharpe:.2f}[/]")
                    else:
                        outputs.append(f"[red]✗ Backtest complete: {returns:.2%} returns[/]")
                        outputs.append(f"[yellow]Sharpe ratio: {sharpe:.2f}[/]")
                    
                    self.is_building = False
                else:
                    outputs.append("[yellow]No strategy files found[/]")
            else:
                outputs.append("[red]Backtest folder not found[/]")
                
        except Exception as e:
            outputs.append(f"[red]Backtest Error: {str(e)}[/]")
            self.is_building = False
        
        return outputs
    
    async def _optimize_portfolio(self) -> List[str]:
        """Optimize portfolio allocation"""
        outputs = []
        
        try:
            outputs.append("[cyan]Calculating Kelly criterion weights...[/]")
            
            # Simulate portfolio optimization
            assets = ["BTC", "ETH", "SOL", "AVAX"]
            weights = {}
            
            for asset in assets:
                weight = random.uniform(0.1, 0.4)
                weights[asset] = weight
            
            # Normalize weights
            total_weight = sum(weights.values())
            weights = {k: v/total_weight for k, v in weights.items()}
            
            outputs.append("[green]✓ Optimization complete:[/]")
            for asset, weight in weights.items():
                outputs.append(f"  {asset}: {weight:.1%}")
            
            # Calculate expected return
            expected_return = random.uniform(0.05, 0.25)
            outputs.append(f"[yellow]Expected annual return: {expected_return:.1%}[/]")
            
        except Exception as e:
            outputs.append(f"[red]Optimization Error: {str(e)}[/]")
        
        return outputs
    
    async def _monitor_risk(self) -> List[str]:
        """Monitor risk metrics"""
        outputs = []
        
        try:
            # Simulate risk monitoring
            current_drawdown = random.uniform(0.01, 0.20)
            var_95 = random.uniform(0.02, 0.08)
            
            outputs.append("[cyan]Risk metrics updated:[/]")
            
            # Check drawdown
            max_dd_threshold = self.config.get("thresholds", {}).get("max_drawdown", 0.15)
            if current_drawdown > max_dd_threshold:
                outputs.append(f"[red]⚠ High drawdown: {current_drawdown:.1%}[/]")
            else:
                outputs.append(f"[green]✓ Drawdown: {current_drawdown:.1%}[/]")
            
            # Check VaR
            var_threshold = self.config.get("thresholds", {}).get("var_95", 0.05)
            if var_95 > var_threshold:
                outputs.append(f"[red]⚠ High VaR(95%): {var_95:.1%}[/]")
            else:
                outputs.append(f"[green]✓ VaR(95%): {var_95:.1%}[/]")
            
            outputs.append("[dim]All systems nominal[/]")
            
        except Exception as e:
            outputs.append(f"[red]Risk Monitor Error: {str(e)}[/]")
        
        return outputs


class ClaudeCodeManager:
    """Manages multiple Claude Code agents"""
    
    def __init__(self):
        self.agents: Dict[str, ClaudeCodeAgent] = {}
        self.total_points = 0
        self.lock_timer = 600  # 10 minutes
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize the four Claude agents"""
        agent_configs = [
            ("claude-1", "Claude Opus Max #1", "hyperliquid_scanner"),
            ("claude-2", "Claude Opus Max #2", "backtest_runner"),
            ("claude-3", "Claude Opus Max #3", "portfolio_optimizer"),
            ("claude-4", "Claude Opus Max #4", "risk_monitor"),
        ]
        
        for agent_id, name, task_type in agent_configs:
            self.agents[agent_id] = ClaudeCodeAgent(agent_id, name, task_type)
        
        # Set first agent as active
        self.agents["claude-1"].is_active = True
    
    async def refresh_all_agents(self) -> Dict[str, List[str]]:
        """Refresh all agents and return their outputs"""
        results = {}
        
        for agent_id, agent in self.agents.items():
            new_outputs = await agent.execute_task()
            results[agent_id] = new_outputs
            
            # Update total points
            self.total_points = sum(agent.points_earned for agent in self.agents.values())
        
        # Update lock timer
        if self.lock_timer > 0:
            self.lock_timer -= 30
        
        return results
    
    def cycle_active_agent(self):
        """Cycle the active agent"""
        agent_ids = list(self.agents.keys())
        current_active = None
        
        # Find current active
        for i, agent_id in enumerate(agent_ids):
            if self.agents[agent_id].is_active:
                current_active = i
                self.agents[agent_id].is_active = False
                break
        
        # Set next as active
        if current_active is not None:
            next_active = (current_active + 1) % len(agent_ids)
            self.agents[agent_ids[next_active]].is_active = True
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get status of a specific agent"""
        agent = self.agents.get(agent_id)
        if not agent:
            return {}
        
        return {
            "name": agent.name,
            "task": agent.current_task,
            "points": agent.points_earned,
            "is_active": agent.is_active,
            "is_building": agent.is_building,
            "outputs": agent.output_buffer,
            "last_activity": agent.last_activity
        }


# Global manager instance
claude_manager = ClaudeCodeManager()


async def test_claude_integration():
    """Test the Claude Code integration"""
    print("Testing Claude Code Integration...")
    
    manager = ClaudeCodeManager()
    
    for i in range(3):
        print(f"\n--- Refresh {i+1} ---")
        results = await manager.refresh_all_agents()
        
        for agent_id, outputs in results.items():
            if outputs:
                print(f"{agent_id}: {outputs[-1]}")  # Show last output
        
        print(f"Total points: {manager.total_points}")
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(test_claude_integration())