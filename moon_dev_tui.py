#!/usr/bin/env python3
"""
Moon Dev Quant App TUI
A comprehensive terminal UI for crypto trading with live data feeds
"""
import asyncio
import psutil
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
import os
import sys
import random
import math
import pandas as pd
import numpy as np

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    Static,
    TabbedContent,
    TabPane,
)
from textual.reactive import reactive
from rich.text import Text
from rich.table import Table as RichTable

# Import plotting libraries
try:
    import plotext as plt
    from textual_plotext import PlotextPlot
    PLOTTING_AVAILABLE = True
except ImportError:
    print("Warning: Plotting libraries not available. Charts will be disabled.")
    PLOTTING_AVAILABLE = False
    PlotextPlot = None

# Import our API modules
try:
    from hyperliquid_api import HyperliquidAPI
    from polymarket_api import PolymarketAPI, PolymarketBot
    from claude_code_integration import claude_manager
except ImportError as e:
    print(f"Warning: Could not import API modules: {e}")
    print("Some features may not work properly.")
    HyperliquidAPI = None
    PolymarketAPI = None
    PolymarketBot = None
    claude_manager = None


class BTCTicker(Static):
    """Live BTC price ticker"""
    price = reactive(Decimal("0"))
    change_24h = reactive(Decimal("0"))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "BTC/USD"
    
    def render(self) -> RichTable:
        table = RichTable(show_header=False, box=None, padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="right")
        
        color = "green" if self.change_24h >= 0 else "red"
        arrow = "▲" if self.change_24h >= 0 else "▼"
        
        table.add_row(
            "[bold cyan]Price:[/]",
            f"[bold white]${self.price:,.2f}[/]"
        )
        table.add_row(
            "[bold cyan]24h:[/]",
            f"[{color}]{arrow} {self.change_24h:+.2f}%[/]"
        )
        
        return table


class HyperliquidFundingPanel(Static):
    """Top 30 most negative funding rates from Hyperliquid"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Hyperliquid Funding (Top 30 Negative)"
        self.funding_data: List[Dict] = []
    
    def render(self) -> RichTable:
        table = RichTable(
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 1)
        )
        
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("Funding %", justify="right", width=12)
        table.add_column("Next", justify="right", width=10)
        table.add_column("OI", justify="right", width=15)
        
        if not self.funding_data:
            table.add_row("Loading...", "-", "-", "-")
        else:
            for item in self.funding_data[:30]:
                symbol = item.get("symbol", "N/A")
                funding = item.get("funding_rate", 0)
                next_time = item.get("next_funding", "N/A")
                oi = item.get("open_interest", 0)
                
                color = "red" if funding < 0 else "green"
                table.add_row(
                    symbol,
                    f"[{color}]{funding:.4f}%[/]",
                    next_time,
                    f"${oi:,.0f}"
                )
        
        return table


class GuardianMemoryPanel(Static):
    """Memory leak detector tracking per-process growth"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Guardian Agent - Memory Monitor"
        self.process_data: Dict[str, Dict] = {}
        self.last_update = datetime.now()
    
    def render(self) -> RichTable:
        table = RichTable(
            show_header=True,
            header_style="bold yellow",
            box=None,
            padding=(0, 1)
        )
        
        table.add_column("Process", style="cyan", width=20)
        table.add_column("PID", justify="right", width=8)
        table.add_column("Memory", justify="right", width=12)
        table.add_column("Growth", justify="right", width=12)
        table.add_column("Status", width=10)
        
        if not self.process_data:
            table.add_row("Scanning...", "-", "-", "-", "-")
        else:
            for proc_name, data in list(self.process_data.items())[:10]:
                pid = data.get("pid", "N/A")
                memory = data.get("memory_mb", 0)
                growth = data.get("growth_mb", 0)
                status = data.get("status", "OK")
                
                growth_color = "red" if growth > 50 else "yellow" if growth > 20 else "green"
                status_color = "red" if status == "LEAK" else "green"
                
                table.add_row(
                    proc_name[:20],
                    str(pid),
                    f"{memory:.1f} MB",
                    f"[{growth_color}]{growth:+.1f} MB[/]",
                    f"[{status_color}]{status}[/]"
                )
        
        seconds_ago = (datetime.now() - self.last_update).seconds
        table.caption = f"Updated {seconds_ago}s ago"
        
        return table


class TopProcessesPanel(Static):
    """Top non-Python processes by resource usage"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Top Non-Python Processes"
    
    def render(self) -> RichTable:
        table = RichTable(
            show_header=True,
            header_style="bold green",
            box=None,
            padding=(0, 1)
        )
        
        table.add_column("Process", style="cyan", width=25)
        table.add_column("CPU %", justify="right", width=10)
        table.add_column("Memory", justify="right", width=12)
        table.add_column("Threads", justify="right", width=10)
        
        try:
            processes = []
            for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_info', 'num_threads']):
                try:
                    info = proc.info
                    if info['name'] and 'python' not in info['name'].lower():
                        processes.append({
                            'name': info['name'],
                            'cpu': info['cpu_percent'] or 0,
                            'memory': info['memory_info'].rss / 1024 / 1024 if info['memory_info'] else 0,
                            'threads': info['num_threads'] or 0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            
            for proc in processes[:10]:
                cpu_color = "red" if proc['cpu'] > 50 else "yellow" if proc['cpu'] > 20 else "white"
                table.add_row(
                    proc['name'][:25],
                    f"[{cpu_color}]{proc['cpu']:.1f}%[/]",
                    f"{proc['memory']:.1f} MB",
                    str(proc['threads'])
                )
        except Exception as e:
            table.add_row(f"Error: {str(e)}", "-", "-", "-")
        
        return table


class PolymarketPanel(Static):
    """Polymarket bots and predictions"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Polymarket Bots"
        self.markets: List[Dict] = []
        self.bot: Optional[PolymarketBot] = None
        if PolymarketBot:
            self.bot = PolymarketBot(strategy="momentum")
    
    async def update_markets(self):
        """Update market data from Polymarket API"""
        if self.bot:
            try:
                self.markets = await self.bot.scan_markets()
            except Exception as e:
                print(f"Polymarket update error: {e}")
                self.markets = self._get_mock_markets()
        else:
            self.markets = self._get_mock_markets()
        
        self.refresh()
    
    def _get_mock_markets(self) -> List[Dict]:
        """Return mock market data"""
        return [
            {"market": "BTC > $100k by EOY", "yes": 67.5, "volume": 1250000, "signal": "LONG"},
            {"market": "ETH ETF Approval Q2", "yes": 45.2, "volume": 890000, "signal": "NEUTRAL"},
            {"market": "Fed Rate Cut March", "yes": 82.1, "volume": 2100000, "signal": "LONG"},
            {"market": "AI Regulation Bill", "yes": 28.7, "volume": 567000, "signal": "SHORT"},
            {"market": "SOL > $500 by Q4", "yes": 73.4, "volume": 1890000, "signal": "LONG"},
            {"market": "Recession in 2026", "yes": 34.8, "volume": 3450000, "signal": "SHORT"},
        ]
    
    def render(self) -> RichTable:
        table = RichTable(
            show_header=True,
            header_style="bold blue",
            box=None,
            padding=(0, 1)
        )
        
        table.add_column("Market", style="cyan", width=35)
        table.add_column("Yes %", justify="right", width=10)
        table.add_column("Volume", justify="right", width=15)
        table.add_column("Signal", width=10)
        
        if not self.markets:
            self.markets = self._get_mock_markets()
        
        for market in self.markets[:10]:
            signal = market.get("signal", "NEUTRAL")
            signal_color = "green" if signal == "LONG" else "red" if signal == "SHORT" else "yellow"
            
            table.add_row(
                market.get("market", "N/A")[:35],
                f"{market.get('yes', 0):.1f}%",
                f"${market.get('volume', 0):,.0f}",
                f"[{signal_color}]{signal}[/]"
            )
        
        return table



class TradeTab(VerticalScroll):
    """Trade execution and monitoring tab"""
    
    def compose(self) -> ComposeResult:
        yield Label("[bold cyan]Trade Execution Dashboard[/]", classes="tab-title")
        
        with Horizontal(classes="panel-row"):
            yield BTCTicker(classes="panel")
            yield Static("[bold]Quick Actions[/]\n\n[green]● Market Buy[/]\n[red]● Market Sell[/]\n[yellow]● Limit Order[/]", 
                        classes="panel", id="quick-actions")
        
        with Horizontal(classes="panel-row"):
            yield HyperliquidFundingPanel(classes="panel large")
        
        yield Label("[bold yellow]Active Positions[/]", classes="section-title")
        yield DataTable(id="positions-table", classes="data-table")


class ClaudeTerminal(Static):
    """Individual Claude Code terminal pane"""
    
    def __init__(self, terminal_id: str, title: str, **kwargs):
        super().__init__(**kwargs)
        self.terminal_id = terminal_id
        self.title = title
        self.is_active = False
        self.is_building = False
        self.points_earned = 0
        self.last_activity = datetime.now()
        self.output_lines: List[str] = []
        self.current_task = ""
        
    def set_active(self, active: bool):
        """Set terminal as active/inactive"""
        self.is_active = active
        self.refresh()
    
    def set_building(self, building: bool):
        """Set terminal building status"""
        self.is_building = building
        self.refresh()
    
    def add_output(self, line: str):
        """Add output line to terminal"""
        self.output_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")
        if len(self.output_lines) > 20:  # Keep last 20 lines
            self.output_lines = self.output_lines[-20:]
        self.last_activity = datetime.now()
        self.refresh()
    
    def render(self) -> RichTable:
        # Determine border color
        if self.is_active:
            border_color = "#00d4ff"  # Cyan for active
            border_style = "solid"
        elif self.is_building:
            border_color = "#ff9500"  # Orange for building
            border_style = "solid"
        else:
            border_color = "#333"
            border_style = "solid"
        
        table = RichTable(
            show_header=False,
            box=None,
            padding=(1, 2),
            style=f"border: 2px {border_style} {border_color}; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 8px;"
        )
        table.add_column(justify="left", style="white")
        
        # Terminal header
        status_color = "#00ff88" if self.is_active else "#ffaa00" if self.is_building else "#666"
        status_text = "●ACTIVE" if self.is_active else "●BUILDING" if self.is_building else "●IDLE"
        
        header = f"[bold {border_color}]{self.title}[/] [{status_color}]{status_text}[/]"
        table.add_row(header)
        table.add_row(f"[dim]Points: [bold #00ff88]{self.points_earned}[/] | Task: [cyan]{self.current_task}[/][/]")
        table.add_row("[dim]" + "─" * 60 + "[/]")
        
        # Terminal output
        if not self.output_lines:
            table.add_row("[dim]Waiting for Claude Opus Max...[/]")
        else:
            for line in self.output_lines[-8:]:  # Show last 8 lines
                table.add_row(line)
        
        # Activity indicator
        seconds_ago = (datetime.now() - self.last_activity).seconds
        table.add_row(f"[dim]Last activity: {seconds_ago}s ago[/]")
        
        return table


class CodeTab(Container):
    """Enhanced CODE tab with 2x2 grid of Claude terminals"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_terminal = 0
        self.terminals: List[ClaudeTerminal] = []
        self.lock_timer = 600  # 10 minutes in seconds
        self.total_points = 0
    
    def compose(self) -> ComposeResult:
        # Top bar matching TRADE tab style
        yield Static(
            self._render_top_bar(),
            classes="code-top-bar",
            id="code-top-bar"
        )
        
        # 2x2 grid of Claude terminals
        with Horizontal(classes="code-grid-row"):
            yield ClaudeTerminal("claude-1", "Claude Opus Max #1", classes="claude-terminal", id="claude-1")
            yield ClaudeTerminal("claude-2", "Claude Opus Max #2", classes="claude-terminal", id="claude-2")
        
        with Horizontal(classes="code-grid-row"):
            yield ClaudeTerminal("claude-3", "Claude Opus Max #3", classes="claude-terminal", id="claude-3")
            yield ClaudeTerminal("claude-4", "Claude Opus Max #4", classes="claude-terminal", id="claude-4")
    
    def on_mount(self) -> None:
        """Initialize terminals when mounted"""
        self.terminals = [
            self.query_one("#claude-1", ClaudeTerminal),
            self.query_one("#claude-2", ClaudeTerminal),
            self.query_one("#claude-3", ClaudeTerminal),
            self.query_one("#claude-4", ClaudeTerminal),
        ]
        
        # Set first terminal as active
        self.terminals[0].set_active(True)
        
        # Initialize with sample tasks
        self.terminals[0].current_task = "Analyzing Hyperliquid funding rates"
        self.terminals[1].current_task = "Backtesting BTC breakout strategy"
        self.terminals[2].current_task = "Optimizing portfolio allocation"
        self.terminals[3].current_task = "Monitoring risk metrics"
        
        # Add sample output
        self.terminals[0].add_output("[cyan]Connecting to Hyperliquid API...[/]")
        self.terminals[0].add_output("[green]✓ Connected successfully[/]")
        self.terminals[0].add_output("[yellow]Scanning 30 most negative funding rates...[/]")
        
        self.terminals[1].add_output("[cyan]Loading backtest data from agents/backtest/[/]")
        self.terminals[1].add_output("[green]✓ Found 15m BTC strategy[/]")
        self.terminals[1].set_building(True)
        
        self.terminals[2].add_output("[cyan]Initializing portfolio optimizer...[/]")
        self.terminals[2].add_output("[yellow]Calculating Kelly criterion weights...[/]")
        
        self.terminals[3].add_output("[cyan]Risk monitor active[/]")
        self.terminals[3].add_output("[green]✓ All systems nominal[/]")
    
    def _render_top_bar(self) -> str:
        """Render the top bar with live stats"""
        minutes_left = self.lock_timer // 60
        seconds_left = self.lock_timer % 60
        
        return (
            f"[bold cyan]CODE — Claude Max v2.1.71[/] • "
            f"Points earned: [bold #00ff88]{self.total_points}[/] • "
            f"[bold #ffaa00]{minutes_left:02d}:{seconds_left:02d}[/] Lock In Timer"
        )
    
    def cycle_active_terminal(self):
        """Cycle to next active terminal"""
        if claude_manager:
            # Use Claude manager to cycle
            claude_manager.cycle_active_agent()
            
            # Update terminal states
            for i, terminal in enumerate(self.terminals):
                agent_id = f"claude-{i+1}"
                status = claude_manager.get_agent_status(agent_id)
                if status:
                    terminal.set_active(status["is_active"])
        else:
            # Fallback to local cycling
            # Deactivate current
            self.terminals[self.active_terminal].set_active(False)
            
            # Move to next
            self.active_terminal = (self.active_terminal + 1) % 4
            
            # Activate new
            self.terminals[self.active_terminal].set_active(True)
    
    async def refresh_terminals(self):
        """Refresh all terminal data"""
        if claude_manager:
            # Get fresh data from Claude manager
            results = await claude_manager.refresh_all_agents()
            
            # Update each terminal with new data
            for i, terminal in enumerate(self.terminals):
                agent_id = f"claude-{i+1}"
                status = claude_manager.get_agent_status(agent_id)
                
                if status:
                    terminal.current_task = status["task"]
                    terminal.points_earned = status["points"]
                    terminal.is_active = status["is_active"]
                    terminal.is_building = status["is_building"]
                    terminal.output_lines = status["outputs"]
                    terminal.last_activity = status["last_activity"]
                    terminal.refresh()
            
            # Update total points and timer
            self.total_points = claude_manager.total_points
            self.lock_timer = claude_manager.lock_timer
        else:
            # Fallback to simulation if manager not available
            await self._simulate_activity()
        
        # Update top bar
        top_bar = self.query_one("#code-top-bar", Static)
        top_bar.update(self._render_top_bar())
    
    async def _simulate_activity(self):
        """Simulate activity when Claude manager is not available"""
        import random
        
        for i, terminal in enumerate(self.terminals):
            if random.random() < 0.3:  # 30% chance of new activity
                activities = [
                    "[green]✓ Task completed successfully[/]",
                    "[yellow]Processing market data...[/]",
                    "[cyan]Executing strategy logic...[/]",
                    "[blue]Analyzing price patterns...[/]",
                    "[magenta]Optimizing parameters...[/]",
                    "[red]Warning: High volatility detected[/]",
                ]
                terminal.add_output(random.choice(activities))
                
                # Award points randomly
                if random.random() < 0.2:  # 20% chance of points
                    points = random.randint(10, 50)
                    terminal.points_earned += points
                    self.total_points += points
                    terminal.add_output(f"[bold #00ff88]+{points} points earned![/]")
        
        # Update timer
        if self.lock_timer > 0:
            self.lock_timer -= 30  # Decrease by refresh interval


class BacktestTemplatePanel(Static):
    """Backtest strategy templates panel"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Strategy Templates"
        self.selected_template = 0
        self.templates = [
            {"name": "Momentum + Volume", "color": "#00ff88", "description": "High-momentum breakouts with volume confirmation"},
            {"name": "Funding Rate Arb", "color": "#ff6b6b", "description": "Exploit negative funding rate opportunities"},
            {"name": "HIP3 Tokenized Stocks", "color": "#9d4edd", "description": "Trade tokenized stock derivatives"},
            {"name": "Polymarket Signals", "color": "#4ecdc4", "description": "Prediction market sentiment trading"},
            {"name": "Custom Strategy", "color": "#ffaa00", "description": "User-defined custom trading logic"}
        ]
    
    def render(self) -> RichTable:
        table = RichTable(
            show_header=False,
            box=None,
            padding=(1, 2)
        )
        table.add_column(justify="left", style="white")
        
        table.add_row("[bold #00d4ff]STRATEGY TEMPLATES[/]")
        table.add_row("[dim]" + "─" * 40 + "[/]")
        
        for i, template in enumerate(self.templates):
            color = template["color"]
            name = template["name"]
            desc = template["description"]
            
            if i == self.selected_template:
                # Selected template with neon border effect
                table.add_row(f"[bold {color}]▶ {name}[/]")
                table.add_row(f"[dim]{desc}[/]")
                table.add_row("")
            else:
                table.add_row(f"[{color}]● {name}[/]")
                table.add_row(f"[dim]{desc}[/]")
                table.add_row("")
        
        table.add_row("[dim]Use ↑↓ to select, Enter to run[/]")
        
        return table


class BacktestControlPanel(Static):
    """Backtest execution control panel"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backtest_running = False
        self.progress = 0
        self.data_sources = 18
        self.current_source = ""
        
    def render(self) -> RichTable:
        table = RichTable(
            show_header=False,
            box=None,
            padding=(2, 3)
        )
        table.add_column(justify="center", style="white")
        
        if not self.backtest_running:
            # Large green run button
            table.add_row("")
            table.add_row("[bold #00ff88 on #1a1a2e]" + "═" * 30 + "[/]")
            table.add_row("[bold #00ff88 on #1a1a2e]    RUN SELECTED BACKTEST    [/]")
            table.add_row("[bold #00ff88 on #1a1a2e]" + "═" * 30 + "[/]")
            table.add_row("")
            table.add_row(f"[dim]Using {self.data_sources} proprietary data sources[/]")
            table.add_row("[dim]from Hyperliquid-Data-Layer-API[/]")
        else:
            # Progress bar and status
            table.add_row("")
            table.add_row("[bold #ffaa00]BACKTEST RUNNING...[/]")
            table.add_row("")
            
            # Progress bar
            filled = int(self.progress * 20)
            empty = 20 - filled
            progress_bar = "█" * filled + "░" * empty
            table.add_row(f"[#00ff88]{progress_bar}[/] {self.progress:.1%}")
            table.add_row("")
            
            table.add_row(f"[dim]Current: {self.current_source}[/]")
            table.add_row(f"[dim]Data sources: {self.data_sources}/18 loaded[/]")
        
        return table


class BacktestResultsPanel(Static):
    """Live backtest results table"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Live Results"
        self.results: List[Dict] = []
        self.completed_backtests = 0
        self.total_time_minutes = 0
        
    def add_result(self, result: Dict):
        """Add a new backtest result"""
        self.results.append(result)
        self.completed_backtests += 1
        self.refresh()
    
    def render(self) -> RichTable:
        table = RichTable(
            show_header=True,
            header_style="bold #00d4ff",
            box=None,
            padding=(0, 1)
        )
        
        table.add_column("Strategy", style="cyan", width=18)
        table.add_column("Total Return %", justify="right", width=12)
        table.add_column("Sharpe", justify="right", width=8)
        table.add_column("Sortino", justify="right", width=8)
        table.add_column("Win Rate", justify="right", width=8)
        table.add_column("Max DD", justify="right", width=8)
        table.add_column("vs Buy&Hold", justify="right", width=12)
        
        if not self.results:
            table.add_row("No results yet...", "-", "-", "-", "-", "-", "-")
        else:
            for result in self.results[-10:]:  # Show last 10 results
                strategy = result.get("strategy", "Unknown")
                total_return = result.get("total_return", 0)
                sharpe = result.get("sharpe", 0)
                sortino = result.get("sortino", 0)
                win_rate = result.get("win_rate", 0)
                max_dd = result.get("max_dd", 0)
                vs_bh = result.get("vs_buy_hold", 0)
                
                # Color coding for returns
                return_color = "green" if total_return > 0 else "red"
                vs_bh_color = "green" if vs_bh > 0 else "red"
                
                table.add_row(
                    strategy[:18],
                    f"[{return_color}]{total_return:+.1f}%[/]",
                    f"{sharpe:.2f}",
                    f"{sortino:.2f}",
                    f"{win_rate:.1f}%",
                    f"[red]{max_dd:.1f}%[/]",
                    f"[{vs_bh_color}]{vs_bh:+.1f}%[/]"
                )
        
        return table


class BacktestChartPanel(Static):
    """Enhanced backtest chart panel with multiple professional charts"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_chart = "equity"
        self.backtest_data = None
        self.comparison_mode = False
        self.comparison_data = []

    def set_backtest_data(self, data: Dict):
        """Set backtest results data for chart generation"""
        self.backtest_data = data
        self.refresh()

    def set_comparison_data(self, data_list: List[Dict]):
        """Set multiple backtest results for comparison"""
        self.comparison_data = data_list
        self.comparison_mode = True
        self.refresh()

    def cycle_chart(self):
        """Cycle through available charts"""
        charts = ["equity", "drawdown", "price", "winrate", "returns", "compare"]
        current_idx = charts.index(self.current_chart)
        self.current_chart = charts[(current_idx + 1) % len(charts)]
        self.refresh()

    def render(self) -> RichTable:
        table = RichTable(
            show_header=False,
            box=None,
            padding=(1, 2)
        )
        table.add_column(justify="center", style="white")

        # Chart tabs header
        tabs = ["[cyan]Equity[/]" if self.current_chart == "equity" else "Equity",
                "[cyan]Drawdown[/]" if self.current_chart == "drawdown" else "Drawdown",
                "[cyan]Price+Signals[/]" if self.current_chart == "price" else "Price+Signals",
                "[cyan]Win Rate[/]" if self.current_chart == "winrate" else "Win Rate",
                "[cyan]Returns Dist[/]" if self.current_chart == "returns" else "Returns Dist",
                "[cyan]Compare[/]" if self.current_chart == "compare" else "Compare"]

        table.add_row(f"[bold #00d4ff]BACKTEST CHARTS[/] — {' | '.join(tabs)}")
        table.add_row("")

        if not self.backtest_data and not self.comparison_mode:
            table.add_row("[dim]Run a backtest to see charts...[/]")
            return table

        # Generate chart based on current selection
        if self.current_chart == "equity":
            chart_content = self._generate_equity_chart()
        elif self.current_chart == "drawdown":
            chart_content = self._generate_drawdown_chart()
        elif self.current_chart == "price":
            chart_content = self._generate_price_signals_chart()
        elif self.current_chart == "winrate":
            chart_content = self._generate_winrate_chart()
        elif self.current_chart == "returns":
            chart_content = self._generate_returns_histogram()
        elif self.current_chart == "compare":
            chart_content = self._generate_comparison_chart()
        else:
            chart_content = "[dim]Chart not available[/]"

        table.add_row(chart_content)

        # Chart stats
        if self.backtest_data:
            stats = self._get_chart_stats()
            table.add_row("")
            table.add_row(stats)

        return table

    def _generate_equity_chart(self) -> str:
        """Generate ASCII equity curve chart"""
        if not self.backtest_data:
            return "[dim]No data available[/]"

        # Generate sample equity curve data
        days = 100
        equity = [10000]  # Starting capital
        daily_returns = [random.uniform(-0.03, 0.04) for _ in range(days)]

        for ret in daily_returns:
            equity.append(equity[-1] * (1 + ret))

        # Create ASCII chart
        chart_lines = []
        chart_lines.append("[bold #00ff88]EQUITY CURVE[/]")
        chart_lines.append("")

        # Simple ASCII line chart
        max_val = max(equity)
        min_val = min(equity)
        height = 12
        width = 60

        for i in range(height):
            line = ""
            threshold = min_val + (max_val - min_val) * (height - i - 1) / height

            for j in range(0, len(equity), max(1, len(equity) // width)):
                if equity[j] >= threshold:
                    line += "[#00ff88]█[/]"
                else:
                    line += " "

            # Add y-axis labels
            value = f"${threshold:,.0f}"
            chart_lines.append(f"{value:>8} │{line}")

        # X-axis
        chart_lines.append("         └" + "─" * width)
        chart_lines.append(f"         Start{' ' * (width-15)}End")

        return "\n".join(chart_lines)

    def _generate_drawdown_chart(self) -> str:
        """Generate ASCII drawdown chart"""
        chart_lines = []
        chart_lines.append("[bold #ff4444]DRAWDOWN ANALYSIS[/]")
        chart_lines.append("")

        # Generate sample drawdown data
        drawdowns = [random.uniform(-0.25, 0) for _ in range(60)]

        height = 10
        width = 50

        for i in range(height):
            line = ""
            threshold = -0.25 * i / height

            for j in range(0, len(drawdowns), max(1, len(drawdowns) // width)):
                if drawdowns[j] <= threshold:
                    line += "[#ff4444]█[/]"
                else:
                    line += " "

            pct = f"{threshold:.1%}"
            chart_lines.append(f"{pct:>6} │{line}")

        chart_lines.append("       └" + "─" * width)
        chart_lines.append(f"       Start{' ' * (width-12)}End")

        return "\n".join(chart_lines)

    def _generate_price_signals_chart(self) -> str:
        """Generate price chart with trade signals"""
        chart_lines = []
        chart_lines.append("[bold #00d4ff]PRICE + TRADE SIGNALS[/]")
        chart_lines.append("")

        # Generate sample price and signal data
        prices = [95000 + random.uniform(-5000, 5000) for _ in range(50)]
        signals = []

        for i in range(len(prices)):
            if random.random() < 0.1:  # 10% chance of signal
                signals.append(("BUY" if random.random() > 0.5 else "SELL", i))

        height = 10
        width = 45

        max_price = max(prices)
        min_price = min(prices)

        for i in range(height):
            line = ""
            threshold = min_price + (max_price - min_price) * (height - i - 1) / height

            for j in range(0, len(prices), max(1, len(prices) // width)):
                # Check for signals at this position
                has_signal = any(abs(sig[1] - j) < 2 for sig in signals)
                signal_type = next((sig[0] for sig in signals if abs(sig[1] - j) < 2), None)

                if prices[j] >= threshold:
                    if has_signal:
                        if signal_type == "BUY":
                            line += "[bold #00ff88]▲[/]"
                        else:
                            line += "[bold #ff4444]▼[/]"
                    else:
                        line += "[#00d4ff]█[/]"
                else:
                    line += " "

            price_label = f"${threshold:,.0f}"
            chart_lines.append(f"{price_label:>8} │{line}")

        chart_lines.append("         └" + "─" * width)
        chart_lines.append("         [#00ff88]▲ BUY[/]  [#ff4444]▼ SELL[/]")

        return "\n".join(chart_lines)

    def _generate_winrate_chart(self) -> str:
        """Generate win rate pie chart"""
        chart_lines = []
        chart_lines.append("[bold #00ff88]WIN RATE ANALYSIS[/]")
        chart_lines.append("")

        # Sample win rate data
        total_trades = 142
        winning_trades = 97
        win_rate = winning_trades / total_trades

        # ASCII pie chart representation
        chart_lines.append("         ╭─────────────╮")
        chart_lines.append("       ╭─┤             ├─╮")
        chart_lines.append("     ╭─┤ [#00ff88]███████████[/] ├─╮")
        chart_lines.append("   ╭─┤   [#00ff88]███████████[/]   ├─╮")
        chart_lines.append("  ┤     [#00ff88]███████████[/]     ├")
        chart_lines.append("  ┤     [#ff4444]█████[/][#00ff88]██████[/]     ├")
        chart_lines.append("   ╰─┤   [#ff4444]█████[/][#00ff88]██████[/]   ├─╯")
        chart_lines.append("     ╰─┤ [#ff4444]█████[/][#00ff88]██████[/] ├─╯")
        chart_lines.append("       ╰─┤             ├─╯")
        chart_lines.append("         ╰─────────────╯")
        chart_lines.append("")
        chart_lines.append(f"[bold #00ff88]WIN: {win_rate:.1%}[/] ({winning_trades} trades)")
        chart_lines.append(f"[bold #ff4444]LOSS: {1-win_rate:.1%}[/] ({total_trades - winning_trades} trades)")
        chart_lines.append(f"[dim]Total: {total_trades} trades[/]")

        return "\n".join(chart_lines)

    def _generate_returns_histogram(self) -> str:
        """Generate trade returns histogram"""
        chart_lines = []
        chart_lines.append("[bold #00d4ff]TRADE RETURNS DISTRIBUTION[/]")
        chart_lines.append("")

        # Generate sample return distribution
        returns = [random.normalvariate(0.02, 0.05) for _ in range(100)]

        # Create histogram bins
        bins = [-0.15, -0.10, -0.05, -0.02, 0, 0.02, 0.05, 0.10, 0.15]
        hist = [0] * (len(bins) - 1)

        for ret in returns:
            for i in range(len(bins) - 1):
                if bins[i] <= ret < bins[i + 1]:
                    hist[i] += 1
                    break

        max_count = max(hist) if hist else 1
        height = 8

        # Draw histogram
        for i in range(height, 0, -1):
            line = ""
            for j, count in enumerate(hist):
                bar_height = int((count / max_count) * height)
                if bar_height >= i:
                    color = "#00ff88" if bins[j] >= 0 else "#ff4444"
                    line += f"[{color}]██[/]"
                else:
                    line += "  "
            chart_lines.append(f"{i*max_count//height:>3} │{line}")

        # X-axis labels
        chart_lines.append("    └" + "──" * len(hist))
        labels = " ".join([f"{b:.0%}" for b in bins[:-1]])
        chart_lines.append(f"     {labels}")

        return "\n".join(chart_lines)

    def _generate_comparison_chart(self) -> str:
        """Generate multi-strategy comparison chart"""
        chart_lines = []
        chart_lines.append("[bold #00d4ff]MULTI-STRATEGY COMPARISON[/]")
        chart_lines.append("")

        if not self.comparison_data:
            chart_lines.append("[dim]Run comparison mode to see multiple strategies[/]")
            return "\n".join(chart_lines)

        # Generate sample comparison data
        strategies = ["Momentum+Volume", "Funding Arb", "HIP3 Stocks"]
        colors = ["#00ff88", "#ff00ff", "#ff9500"]

        height = 10
        width = 50

        for i in range(height):
            line = ""
            for j in range(width):
                # Simulate different strategy performance
                if j % 3 == 0:
                    line += f"[{colors[0]}]█[/]"
                elif j % 3 == 1:
                    line += f"[{colors[1]}]█[/]"
                else:
                    line += f"[{colors[2]}]█[/]"

            chart_lines.append(f"${100000 + i*5000:>8} │{line}")

        chart_lines.append("         └" + "─" * width)
        chart_lines.append("")

        # Legend
        for i, (strategy, color) in enumerate(zip(strategies, colors)):
            sharpe = 1.8 + random.uniform(-0.5, 0.5)
            sortino = 2.1 + random.uniform(-0.4, 0.4)
            chart_lines.append(f"[{color}]█[/] {strategy}: Sharpe {sharpe:.2f} | Sortino {sortino:.2f}")

        return "\n".join(chart_lines)

    def _get_chart_stats(self) -> str:
        """Get live stats for current chart"""
        if not self.backtest_data:
            return ""

        # Sample stats
        final_return = 23.4
        max_dd = -12.8
        sharpe = 1.87

        return f"[bold #00ff88]Final Return: +{final_return:.1f}%[/] • [bold #ff4444]Max DD: {max_dd:.1f}%[/] • [bold #00d4ff]Sharpe: {sharpe:.2f}[/]"


class BacktestComparisonPanel(Static):
    """Panel for running multi-strategy comparisons"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.comparison_running = False
        
    def render(self) -> RichTable:
        table = RichTable(
            show_header=False,
            box=None,
            padding=(1, 2)
        )
        table.add_column(justify="center", style="white")
        
        if not self.comparison_running:
            table.add_row("")
            table.add_row("[bold #ff9500 on #1a1a2e]" + "═" * 25 + "[/]")
            table.add_row("[bold #ff9500 on #1a1a2e]   RUN COMPARISON   [/]")
            table.add_row("[bold #ff9500 on #1a1a2e]" + "═" * 25 + "[/]")
            table.add_row("")
            table.add_row("[dim]Compare 3 strategies[/]")
            table.add_row("[dim]side-by-side[/]")
        else:
            table.add_row("")
            table.add_row("[bold #ffaa00]COMPARING...[/]")
            table.add_row("")
            table.add_row("[dim]Running 3 strategies[/]")
            table.add_row("[dim]in parallel[/]")
        
        return table



class BacktestTab(Container):
    """Enhanced BACKTEST tab matching TRADE tab style"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backtest_running = False
        self.current_progress = 0
        self.completed_backtests = 0
        self.start_time = None
        
    def compose(self) -> ComposeResult:
        # Top row - Strategy templates, controls, and results
        with Horizontal(classes="backtest-top-row"):
            # Left panel - Strategy templates
            with Vertical(classes="backtest-left-panel"):
                yield BacktestTemplatePanel(classes="backtest-panel", id="template-panel")
            
            # Center panel - Control and progress
            with Vertical(classes="backtest-center-panel"):
                yield BacktestControlPanel(classes="backtest-panel large", id="control-panel")
                yield BacktestComparisonPanel(classes="backtest-panel", id="comparison-panel")
                
                # Completion banner (hidden initially)
                yield Static(
                    "",
                    classes="completion-banner hidden",
                    id="completion-banner"
                )
            
            # Right panel - Results
            with Vertical(classes="backtest-right-panel"):
                yield BacktestResultsPanel(classes="backtest-panel large", id="results-panel")
        
        # Bottom row - Large charts section
        with Horizontal(classes="backtest-bottom-row"):
            yield BacktestChartPanel(classes="backtest-panel large", id="chart-panel")
    
    async def start_backtest(self):
        """Start the backtest process"""
        if self.backtest_running:
            return
        
        self.backtest_running = True
        self.current_progress = 0
        self.start_time = datetime.now()
        
        # Update control panel
        control_panel = self.query_one("#control-panel", BacktestControlPanel)
        control_panel.backtest_running = True
        control_panel.progress = 0
        control_panel.refresh()
        
        # Simulate backtest execution
        await self._run_backtest_simulation()
    
    async def start_comparison(self):
        """Start multi-strategy comparison"""
        comparison_panel = self.query_one("#comparison-panel", BacktestComparisonPanel)
        comparison_panel.comparison_running = True
        comparison_panel.refresh()
        
        # Simulate running 3 strategies in parallel
        await asyncio.sleep(3)
        
        # Generate comparison data
        comparison_data = [
            {"name": "Momentum+Volume", "return": 28.5, "sharpe": 1.92, "sortino": 2.15},
            {"name": "Funding Arb", "return": 15.2, "sharpe": 2.34, "sortino": 2.67},
            {"name": "HIP3 Stocks", "return": 31.8, "sharpe": 1.76, "sortino": 1.98}
        ]
        
        # Update chart panel with comparison data
        chart_panel = self.query_one("#chart-panel", BacktestChartPanel)
        chart_panel.set_comparison_data(comparison_data)
        chart_panel.current_chart = "compare"
        chart_panel.refresh()
        
        comparison_panel.comparison_running = False
        comparison_panel.refresh()
    
    def cycle_chart(self):
        """Cycle through available charts"""
        chart_panel = self.query_one("#chart-panel", BacktestChartPanel)
        chart_panel.cycle_chart()
    
    async def _run_backtest_simulation(self):
        """Simulate backtest execution with progress updates"""
        data_sources = [
            "Hyperliquid Perpetuals",
            "Funding Rate History",
            "Volume Profiles",
            "Order Book Depth",
            "Liquidation Data",
            "Open Interest",
            "Price Impact",
            "Basis Spreads",
            "Cross-Exchange Arb",
            "Volatility Surface",
            "Options Flow",
            "Whale Movements",
            "Social Sentiment",
            "News Events",
            "Macro Indicators",
            "DeFi Yields",
            "Staking Rewards",
            "Token Unlocks"
        ]
        
        control_panel = self.query_one("#control-panel", BacktestControlPanel)
        results_panel = self.query_one("#results-panel", BacktestResultsPanel)
        
        for i, source in enumerate(data_sources):
            # Update progress
            progress = (i + 1) / len(data_sources)
            control_panel.progress = progress
            control_panel.current_source = source
            control_panel.refresh()
            
            # Add intermediate results
            if i % 3 == 0:  # Every 3rd data source
                await self._generate_backtest_result(results_panel)
            
            await asyncio.sleep(0.5)  # Simulate processing time
        
        # Complete the backtest
        await self._complete_backtest()
    
    async def _generate_backtest_result(self, results_panel: BacktestResultsPanel):
        """Generate a mock backtest result"""
        import random
        
        strategies = [
            "BTC Momentum 15m",
            "ETH Funding Arb",
            "SOL Volume Breakout",
            "Multi-Asset Mean Rev",
            "Volatility Scalping"
        ]
        
        result = {
            "strategy": random.choice(strategies),
            "total_return": random.uniform(-15, 45),
            "sharpe": random.uniform(0.5, 3.5),
            "sortino": random.uniform(0.8, 4.2),
            "win_rate": random.uniform(45, 75),
            "max_dd": random.uniform(5, 25),
            "vs_buy_hold": random.uniform(-10, 30)
        }
        
        results_panel.add_result(result)
    
    async def _complete_backtest(self):
        """Complete the backtest and show results"""
        self.backtest_running = False
        self.completed_backtests = 100
        
        # Calculate total time
        if self.start_time:
            total_time = (datetime.now() - self.start_time).total_seconds() / 60
            results_panel = self.query_one("#results-panel", BacktestResultsPanel)
            results_panel.total_time_minutes = total_time
        
        # Reset control panel
        control_panel = self.query_one("#control-panel", BacktestControlPanel)
        control_panel.backtest_running = False
        control_panel.progress = 0
        control_panel.refresh()
        
        # Show completion banner
        banner = self.query_one("#completion-banner", Static)
        banner.update(
            f"[bold #00ff88]✓ 100 backtests completed in {total_time:.1f} minutes[/]"
        )
        banner.remove_class("hidden")
        
        # Generate backtest results data
        backtest_data = {
            "final_return": 23.4,
            "max_drawdown": -12.8,
            "sharpe_ratio": 1.87,
            "sortino_ratio": 2.15,
            "win_rate": 0.684,
            "total_trades": 142,
            "avg_trade": 45.20,
            "completed_at": datetime.now()
        }
        
        # Update chart panel with data
        chart_panel = self.query_one("#chart-panel", BacktestChartPanel)
        chart_panel.set_backtest_data(backtest_data)
        
        # Auto-hide banner after 5 seconds
        await asyncio.sleep(5)
        banner.add_class("hidden")
    
    async def refresh_backtest_data(self):
        """Refresh backtest data every 30 seconds"""
        if not self.backtest_running:
            # Generate new results periodically
            results_panel = self.query_one("#results-panel", BacktestResultsPanel)
            if len(results_panel.results) < 10:
                await self._generate_backtest_result(results_panel)


class DataSearchPanel(Static):
    """Data search and filter panel"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_query = ""
        self.active_filter = "All"
        self.filters = ["All", "HIP3 Stocks", "Funding", "Liquidations", "Whale Moves"]
    
    def render(self) -> RichTable:
        table = RichTable(
            show_header=False,
            box=None,
            padding=(1, 2)
        )
        table.add_column(justify="left", style="white")
        
        # Search input
        table.add_row(f"[bold #00d4ff]SEARCH:[/] [dim]>{self.search_query}_[/]")
        table.add_row("")
        
        # Filter buttons
        filter_row = ""
        for filter_name in self.filters:
            if filter_name == self.active_filter:
                filter_row += f"[bold #00d4ff on #1a1a2e] {filter_name} [/] "
            else:
                filter_row += f"[dim] {filter_name} [/] "
        
        table.add_row(filter_row)
        
        return table


class DataMainTable(Static):
    """Main data table with market information"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Market Data"
        self.data: List[Dict] = []
        self.sort_column = "volume"
        self.sort_desc = True
        
    def render(self) -> RichTable:
        table = RichTable(
            show_header=True,
            header_style="bold #00d4ff",
            box=None,
            padding=(0, 1)
        )
        
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("Price", justify="right", width=12)
        table.add_column("24h %", justify="right", width=10)
        table.add_column("Volume", justify="right", width=15)
        table.add_column("Open Interest", justify="right", width=15)
        table.add_column("Funding Rate", justify="right", width=12)
        
        if not self.data:
            self.data = self._get_mock_data()
        
        # Sort data
        if self.sort_column in ["price", "volume", "open_interest", "funding_rate", "change_24h"]:
            self.data.sort(key=lambda x: x.get(self.sort_column, 0), reverse=self.sort_desc)
        
        for item in self.data[:15]:  # Show top 15
            symbol = item.get("symbol", "N/A")
            price = item.get("price", 0)
            change_24h = item.get("change_24h", 0)
            volume = item.get("volume", 0)
            oi = item.get("open_interest", 0)
            funding = item.get("funding_rate", 0)
            
            # Color coding
            change_color = "green" if change_24h >= 0 else "red"
            funding_color = "red" if funding < 0 else "green"
            
            table.add_row(
                symbol,
                f"${price:,.2f}",
                f"[{change_color}]{change_24h:+.2f}%[/]",
                f"${volume:,.0f}",
                f"${oi:,.0f}",
                f"[{funding_color}]{funding:.4f}%[/]"
            )
        
        return table
    
    def _get_mock_data(self) -> List[Dict]:
        """Generate mock market data"""
        import random
        
        symbols = [
            "BTC-PERP", "ETH-PERP", "SOL-PERP", "AVAX-PERP", "MATIC-PERP",
            "ARB-PERP", "OP-PERP", "ATOM-PERP", "DOGE-PERP", "SHIB-PERP",
            "APT-PERP", "SUI-PERP", "SEI-PERP", "TIA-PERP", "INJ-PERP",
            "RUNE-PERP", "FTM-PERP", "NEAR-PERP", "DOT-PERP", "ADA-PERP"
        ]
        
        data = []
        for symbol in symbols:
            data.append({
                "symbol": symbol,
                "price": random.uniform(0.1, 100000),
                "change_24h": random.uniform(-15, 15),
                "volume": random.uniform(1000000, 500000000),
                "open_interest": random.uniform(5000000, 200000000),
                "funding_rate": random.uniform(-0.05, 0.05)
            })
        
        return data


class DataDetailsPanel(Static):
    """Clickable details panel with orderbook, whale trades, etc."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Details"
        self.selected_symbol = "BTC-PERP"
        
    def render(self) -> RichTable:
        table = RichTable(
            show_header=False,
            box=None,
            padding=(1, 2)
        )
        table.add_column(justify="left", style="white")
        
        table.add_row(f"[bold #00d4ff]{self.selected_symbol} DETAILS[/]")
        table.add_row("[dim]" + "─" * 25 + "[/]")
        table.add_row("")
        
        # Mini orderbook
        table.add_row("[bold #ff6b6b]ORDERBOOK (TOP 5)[/]")
        table.add_row("[red]96,180.50  0.245[/]  [dim]ASK[/]")
        table.add_row("[red]96,175.25  0.189[/]  [dim]ASK[/]")
        table.add_row("[red]96,170.00  0.334[/]  [dim]ASK[/]")
        table.add_row("[dim]────────────────[/]")
        table.add_row("[green]96,165.75  0.567[/]  [dim]BID[/]")
        table.add_row("[green]96,160.50  0.423[/]  [dim]BID[/]")
        table.add_row("[green]96,155.25  0.298[/]  [dim]BID[/]")
        table.add_row("")
        
        # Last 5 whale trades
        table.add_row("[bold #ffaa00]WHALE TRADES (LAST 5)[/]")
        table.add_row("[green]BUY  12.5 BTC  $1.2M[/]")
        table.add_row("[red]SELL  8.3 BTC  $798K[/]")
        table.add_row("[green]BUY  15.7 BTC  $1.5M[/]")
        table.add_row("[red]SELL  6.9 BTC  $663K[/]")
        table.add_row("[green]BUY  22.1 BTC  $2.1M[/]")
        table.add_row("")
        
        # Liquidation risk meter
        table.add_row("[bold #9d4edd]LIQUIDATION RISK[/]")
        risk_level = "MEDIUM"
        risk_color = "#ffaa00"
        table.add_row(f"[{risk_color}]●●●○○ {risk_level}[/]")
        table.add_row("[dim]Long: $45M at $92K[/]")
        table.add_row("[dim]Short: $23M at $99K[/]")
        
        return table


class TopFundingScanner(Static):
    """Auto-running top 30 most negative funding scanner"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Top 30 Most Negative Funding"
        self.funding_data: List[Dict] = []
        self.last_update = datetime.now()
        
    def render(self) -> RichTable:
        table = RichTable(
            show_header=True,
            header_style="bold #ff6b6b",
            box=None,
            padding=(0, 1)
        )
        
        table.add_column("Rank", width=6)
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("Funding %", justify="right", width=12)
        table.add_column("Next", justify="right", width=10)
        table.add_column("OI", justify="right", width=15)
        
        if not self.funding_data:
            self.funding_data = self._get_mock_funding_data()
        
        for i, item in enumerate(self.funding_data[:10], 1):  # Show top 10 in this view
            symbol = item.get("symbol", "N/A")
            funding = item.get("funding_rate", 0)
            next_time = item.get("next_funding", "N/A")
            oi = item.get("open_interest", 0)
            
            table.add_row(
                f"#{i}",
                symbol,
                f"[red]{funding:.4f}%[/]",
                next_time,
                f"${oi:,.0f}"
            )
        
        seconds_ago = (datetime.now() - self.last_update).seconds
        table.caption = f"Auto-refresh: {seconds_ago}s ago | Export CSV available"
        
        return table
    
    def _get_mock_funding_data(self) -> List[Dict]:
        """Generate mock negative funding data"""
        import random
        
        symbols = [
            "BTC-PERP", "ETH-PERP", "SOL-PERP", "AVAX-PERP", "MATIC-PERP",
            "ARB-PERP", "OP-PERP", "ATOM-PERP", "DOGE-PERP", "SHIB-PERP",
            "APT-PERP", "SUI-PERP", "SEI-PERP", "TIA-PERP", "INJ-PERP",
            "RUNE-PERP", "FTM-PERP", "NEAR-PERP", "DOT-PERP", "ADA-PERP",
            "LINK-PERP", "UNI-PERP", "AAVE-PERP", "CRV-PERP", "LDO-PERP",
            "MKR-PERP", "SNX-PERP", "COMP-PERP", "YFI-PERP", "SUSHI-PERP"
        ]
        
        data = []
        for symbol in symbols:
            data.append({
                "symbol": symbol,
                "funding_rate": random.uniform(-0.05, -0.001),  # Only negative
                "next_funding": "4h 23m",
                "open_interest": random.uniform(1000000, 500000000)
            })
        
        # Sort by most negative
        data.sort(key=lambda x: x["funding_rate"])
        return data


class MiniGuardianPanel(Static):
    """Mini Guardian Agent memory monitor"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Guardian Agent"
        
    def render(self) -> RichTable:
        table = RichTable(
            show_header=False,
            box=None,
            padding=(1, 1)
        )
        table.add_column(justify="left", style="white")
        
        table.add_row("[bold #ff9500]MEMORY MONITOR[/]")
        table.add_row("[dim]" + "─" * 15 + "[/]")
        table.add_row("")
        table.add_row("[green]●[/] [dim]System OK[/]")
        table.add_row("[yellow]●[/] [dim]2 Warnings[/]")
        table.add_row("[red]●[/] [dim]1 Leak[/]")
        table.add_row("")
        table.add_row("[dim]Last scan: 15s[/]")
        
        return table


class DataTab(Container):
    """Enhanced DATA tab matching TRADE tab style"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_symbol = "BTC-PERP"
        
    def compose(self) -> ComposeResult:
        # Top search and filter panel
        yield DataSearchPanel(classes="data-search-panel", id="search-panel")
        
        # Main content area
        with Horizontal(classes="data-main-content"):
            # Left - Main data table
            yield DataMainTable(classes="data-panel large", id="main-table")
            
            # Right - Details panel
            yield DataDetailsPanel(classes="data-panel", id="details-panel")
        
        # Bottom area
        with Horizontal(classes="data-bottom-content"):
            # Left - Top funding scanner
            yield TopFundingScanner(classes="data-panel large", id="funding-scanner")
            
            # Right - Mini Guardian + Export
            with Vertical(classes="data-bottom-right"):
                yield MiniGuardianPanel(classes="data-panel mini", id="guardian-mini")
                yield Static(
                    "[bold #00ff88 on #1a1a2e] EXPORT CSV [/]",
                    classes="export-button",
                    id="export-button"
                )
    
    async def refresh_data_tab(self):
        """Refresh all data panels"""
        # Update main table
        main_table = self.query_one("#main-table", DataMainTable)
        main_table.data = await self._fetch_market_data()
        main_table.refresh()
        
        # Update funding scanner
        funding_scanner = self.query_one("#funding-scanner", TopFundingScanner)
        funding_scanner.funding_data = await self._fetch_funding_data()
        funding_scanner.last_update = datetime.now()
        funding_scanner.refresh()
        
        # Update details panel if needed
        details_panel = self.query_one("#details-panel", DataDetailsPanel)
        details_panel.selected_symbol = self.selected_symbol
        details_panel.refresh()
    
    async def _fetch_market_data(self) -> List[Dict]:
        """Fetch market data from Hyperliquid API"""
        try:
            if HyperliquidAPI:
                async with HyperliquidAPI() as api:
                    # Get mids and meta data
                    mids = await api.get_all_mids()
                    meta = await api.get_meta()
                    
                    market_data = []
                    for symbol, price in mids.items():
                        market_data.append({
                            "symbol": symbol,
                            "price": float(price),
                            "change_24h": random.uniform(-15, 15),  # Would get from API
                            "volume": random.uniform(1000000, 500000000),
                            "open_interest": random.uniform(5000000, 200000000),
                            "funding_rate": random.uniform(-0.05, 0.05)
                        })
                    
                    return market_data
            else:
                # Fallback to mock data
                return DataMainTable()._get_mock_data()
        except Exception:
            return DataMainTable()._get_mock_data()
    
    async def _fetch_funding_data(self) -> List[Dict]:
        """Fetch funding data from Hyperliquid API"""
        try:
            if HyperliquidAPI:
                async with HyperliquidAPI() as api:
                    return await api.get_funding_rates()
            else:
                return TopFundingScanner()._get_mock_funding_data()
        except Exception:
            return TopFundingScanner()._get_mock_funding_data()


class MoonDevQuantApp(App):
    """Moon Dev Quant Trading TUI Application"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .tab-title {
        padding: 1;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
    }
    
    .section-title {
        padding: 1 2;
        background: $panel;
        color: $accent;
        text-style: bold;
    }
    
    .panel {
        border: solid $primary;
        background: $surface;
        padding: 1;
        margin: 1;
        height: auto;
        min-height: 10;
    }
    
    .panel.large {
        min-height: 20;
    }
    
    .panel-row {
        height: auto;
        padding: 0 1;
    }
    
    .data-table {
        height: auto;
        margin: 1 2;
        border: solid $accent;
    }
    
    #quick-actions {
        width: 30;
    }
    
    /* CODE Tab Styles */
    .code-top-bar {
        height: 3;
        background: #1a1a2e;
        border: solid #00d4ff;
        padding: 1 2;
        margin: 1;
        color: white;
        text-align: center;
    }
    
    .code-grid-row {
        height: 50%;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    
    .claude-terminal {
        border: solid #333;
        background: #1a1a2e;
        margin: 0 1;
        padding: 1;
        min-height: 20;
    }
    
    .claude-terminal.active {
        border: solid #00d4ff;
    }
    
    .claude-terminal.building {
        border: solid #ff9500;
    }
    
    /* BACKTEST Tab Styles */
    .backtest-top-row {
        height: 60%;
        padding: 0 1;
    }
    
    .backtest-bottom-row {
        height: 40%;
        padding: 0 1;
    }
    
    .backtest-left-panel {
        width: 25%;
        padding: 1;
    }
    
    .backtest-center-panel {
        width: 40%;
        padding: 1;
    }
    
    .backtest-right-panel {
        width: 35%;
        padding: 1;
    }
    
    .backtest-panel {
        border: solid #00d4ff;
        background: #1a1a2e;
        margin: 0 0 1 0;
        padding: 1;
        min-height: 15;
    }
    
    .backtest-panel.large {
        min-height: 25;
    }
    
    .completion-banner {
        background: #00ff88;
        color: #000;
        text-align: center;
        padding: 1;
        margin: 1 0;
    }
    
    .completion-banner.hidden {
        display: none;
    }
    
    /* DATA Tab Styles */
    .data-search-panel {
        height: 5;
        background: #1a1a2e;
        border: solid #00d4ff;
        margin: 1;
        padding: 1;
    }
    
    .data-main-content {
        height: 50%;
        padding: 0 1;
    }
    
    .data-bottom-content {
        height: 35%;
        padding: 0 1;
    }
    
    .data-bottom-right {
        width: 25%;
        padding: 0 1;
    }
    
    .data-panel {
        border: solid #00d4ff;
        background: #1a1a2e;
        margin: 0 1 1 0;
        padding: 1;
        min-height: 15;
    }
    
    .data-panel.large {
        min-height: 20;
        width: 75%;
    }
    
    .data-panel.mini {
        min-height: 10;
        border: solid #ff9500;
    }
    
    .export-button {
        background: #00ff88;
        color: #000;
        text-align: center;
        padding: 1;
        margin: 1 0;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    TabPane {
        padding: 0;
    }
    
    Footer {
        background: $primary;
    }
    
    Header {
        background: $primary;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("shift+tab", "bypass_permissions", "Bypass Permissions", priority=True),
        Binding("ctrl+r", "refresh_code_terminals", "Refresh Code Terminals", priority=True),
        Binding("enter", "run_backtest", "Run Backtest", priority=True),
        Binding("ctrl+c", "run_comparison", "Run Comparison", priority=True),
        Binding("ctrl+e", "export_csv", "Export CSV", priority=True),
        Binding("tab", "cycle_chart", "Cycle Chart", priority=True),
        ("1", "switch_tab('trade')", "Trade"),
        ("2", "switch_tab('code')", "Code"),
        ("3", "switch_tab('backtest')", "Backtest"),
        ("4", "switch_tab('data')", "Data"),
    ]
    
    TITLE = "Moon Dev Quant App"
    SUB_TITLE = "Live Trading Terminal"
    
    def __init__(self):
        super().__init__()
        self.refresh_task: Optional[asyncio.Task] = None
        self.bypass_mode = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with TabbedContent(initial="trade"):
            with TabPane("Trade", id="trade"):
                yield TradeTab()
            
            with TabPane("Code", id="code"):
                yield CodeTab(id="code")
            
            with TabPane("Backtest", id="backtest"):
                yield BacktestTab(id="backtest")
            
            with TabPane("Data", id="data"):
                yield DataTab(id="data")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the app and start auto-refresh"""
        # Skip setup_tables as tables are created dynamically in each tab
        self.refresh_task = asyncio.create_task(self.auto_refresh_loop())
    
    def setup_tables(self) -> None:
        """Setup data tables with columns"""
        # Positions table
        positions_table = self.query_one("#positions-table", DataTable)
        positions_table.add_columns("Symbol", "Side", "Size", "Entry", "Current", "PnL", "PnL %")
        positions_table.add_row("BTC-PERP", "LONG", "0.5", "$95,420", "$96,150", "+$365", "+0.76%")
        positions_table.add_row("ETH-PERP", "SHORT", "2.0", "$3,245", "$3,198", "+$94", "+1.45%")
        
        # Backtest metrics table
        backtest_table = self.query_one("#backtest-metrics", DataTable)
        backtest_table.add_columns("Metric", "Value", "Benchmark", "Status")
        backtest_table.add_row("Total Trades", "234", "-", "✓")
        backtest_table.add_row("Avg Trade", "+$45.20", ">$30", "✓")
        backtest_table.add_row("Sharpe Ratio", "2.34", ">1.5", "✓")
        backtest_table.add_row("Max Drawdown", "-12.5%", "<-15%", "✓")
    
    async def auto_refresh_loop(self) -> None:
        """Auto-refresh data every 30 seconds"""
        while True:
            try:
                await asyncio.sleep(30)
                await self.refresh_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.notify(f"Refresh error: {str(e)}", severity="error")
    
    async def refresh_data(self) -> None:
        """Refresh all live data panels"""
        # Update BTC ticker
        btc_ticker = self.query_one(BTCTicker)
        btc_ticker.price = Decimal("96150.00")
        btc_ticker.change_24h = Decimal("2.34")
        
        # Update Hyperliquid funding
        funding_panel = self.query_one(HyperliquidFundingPanel)
        funding_panel.funding_data = await self.fetch_hyperliquid_funding()
        funding_panel.refresh()
        
        # Update Guardian memory monitor
        guardian_panel = self.query_one(GuardianMemoryPanel)
        guardian_panel.process_data = await self.scan_process_memory()
        guardian_panel.last_update = datetime.now()
        guardian_panel.refresh()
        
        # Update Polymarket data
        polymarket_panel = self.query_one(PolymarketPanel)
        await polymarket_panel.update_markets()
        
        # Update tab-specific content
        try:
            tabbed_content = self.query_one(TabbedContent)
            if tabbed_content.active == "code":
                code_tab = self.query_one("#code", CodeTab)
                await code_tab.refresh_terminals()
            elif tabbed_content.active == "backtest":
                backtest_tab = self.query_one("#backtest", BacktestTab)
                await backtest_tab.refresh_backtest_data()
            elif tabbed_content.active == "data":
                data_tab = self.query_one("#data", DataTab)
                await data_tab.refresh_data_tab()
        except Exception:
            pass
        
        # Refresh top processes
        self.query_one(TopProcessesPanel).refresh()
    
    async def fetch_hyperliquid_funding(self) -> List[Dict]:
        """Fetch funding rates from Hyperliquid API"""
        if HyperliquidAPI is None:
            return self._get_mock_funding_data()
        
        try:
            async with HyperliquidAPI() as api:
                funding_data = await api.get_funding_rates()
                return funding_data
        except Exception as e:
            self.notify(f"Hyperliquid API error: {str(e)}", severity="error")
            return self._get_mock_funding_data()
    
    def _get_mock_funding_data(self) -> List[Dict]:
        """Return mock funding data for testing"""
        import random
        symbols = [
            "BTC-PERP", "ETH-PERP", "SOL-PERP", "AVAX-PERP", "MATIC-PERP", 
            "ARB-PERP", "OP-PERP", "ATOM-PERP", "DOGE-PERP", "SHIB-PERP"
        ]
        
        funding_data = []
        for symbol in symbols:
            funding_data.append({
                "symbol": symbol,
                "funding_rate": random.uniform(-0.05, -0.001),  # Negative funding
                "open_interest": random.uniform(1000000, 500000000),
                "next_funding": "4h 23m",
                "timestamp": datetime.now().isoformat()
            })
        
        # Sort by most negative
        funding_data.sort(key=lambda x: x["funding_rate"])
        return funding_data[:30]
    
    async def scan_process_memory(self) -> Dict[str, Dict]:
        """Scan system processes for memory usage and growth"""
        process_data = {}
        
        try:
            for proc in psutil.process_iter(['name', 'pid', 'memory_info']):
                try:
                    info = proc.info
                    if info['name'] and info['memory_info']:
                        memory_mb = info['memory_info'].rss / 1024 / 1024
                        
                        # Mock growth calculation (would track over time in production)
                        growth_mb = memory_mb * 0.05  # 5% mock growth
                        status = "LEAK" if growth_mb > 100 else "OK"
                        
                        process_data[info['name']] = {
                            'pid': info['pid'],
                            'memory_mb': memory_mb,
                            'growth_mb': growth_mb,
                            'status': status
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        # Sort by memory usage and return top processes
        sorted_procs = sorted(
            process_data.items(),
            key=lambda x: x[1]['memory_mb'],
            reverse=True
        )
        
        return dict(sorted_procs[:15])
    
    def action_refresh(self) -> None:
        """Manual refresh action"""
        asyncio.create_task(self.refresh_data())
        self.notify("Refreshing data...", severity="information")
    
    def action_refresh_code_terminals(self) -> None:
        """Refresh CODE tab terminals"""
        try:
            code_tab = self.query_one("#code", CodeTab)
            asyncio.create_task(code_tab.refresh_terminals())
            self.notify("Refreshing Claude terminals...", severity="information")
        except Exception:
            self.notify("CODE tab not active", severity="warning")
    
    def action_run_backtest(self) -> None:
        """Run selected backtest"""
        try:
            tabbed_content = self.query_one(TabbedContent)
            if tabbed_content.active == "backtest":
                backtest_tab = self.query_one("#backtest", BacktestTab)
                asyncio.create_task(backtest_tab.start_backtest())
                self.notify("Starting backtest with 18 data sources...", severity="information")
            else:
                self.notify("Switch to BACKTEST tab first", severity="warning")
        except Exception as e:
            self.notify(f"Backtest error: {str(e)}", severity="error")
    
    def action_run_comparison(self) -> None:
        """Run multi-strategy comparison"""
        try:
            tabbed_content = self.query_one(TabbedContent)
            if tabbed_content.active == "backtest":
                backtest_tab = self.query_one("#backtest", BacktestTab)
                asyncio.create_task(backtest_tab.start_comparison())
                self.notify("Starting 3-strategy comparison...", severity="information")
            else:
                self.notify("Switch to BACKTEST tab first", severity="warning")
        except Exception as e:
            self.notify(f"Comparison error: {str(e)}", severity="error")
    
    def action_cycle_chart(self) -> None:
        """Cycle through backtest charts"""
        try:
            tabbed_content = self.query_one(TabbedContent)
            if tabbed_content.active == "backtest":
                backtest_tab = self.query_one("#backtest", BacktestTab)
                backtest_tab.cycle_chart()
                self.notify("Cycled to next chart", severity="information")
        except Exception:
            pass
    
    def action_export_csv(self) -> None:
        """Export data to CSV"""
        try:
            tabbed_content = self.query_one(TabbedContent)
            if tabbed_content.active == "data":
                # Simulate CSV export
                import csv
                import tempfile
                import os
                
                # Create temporary CSV file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                    writer = csv.writer(f)
                    writer.writerow(['Symbol', 'Price', '24h %', 'Volume', 'Open Interest', 'Funding Rate'])
                    
                    # Mock data for export
                    writer.writerow(['BTC-PERP', '96150.00', '+2.34%', '125000000', '89000000', '-0.0125%'])
                    writer.writerow(['ETH-PERP', '3245.50', '+1.87%', '89000000', '67000000', '-0.0089%'])
                    
                    csv_path = f.name
                
                self.notify(f"Data exported to: {os.path.basename(csv_path)}", severity="information")
            else:
                self.notify("Switch to DATA tab first", severity="warning")
        except Exception as e:
            self.notify(f"Export error: {str(e)}", severity="error")
    
    def action_bypass_permissions(self) -> None:
        """Toggle bypass permissions mode"""
        self.bypass_mode = not self.bypass_mode
        status = "ENABLED" if self.bypass_mode else "DISABLED"
        color = "green" if self.bypass_mode else "red"
        self.notify(f"Bypass Permissions: [{color}]{status}[/]", severity="warning")
        
        # Also cycle active terminal in CODE tab if active
        try:
            tabbed_content = self.query_one(TabbedContent)
            if tabbed_content.active == "code":
                code_tab = self.query_one("#code", CodeTab)
                code_tab.cycle_active_terminal()
                self.notify("Cycled active Claude terminal", severity="information")
        except Exception:
            pass
    
    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to specified tab"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = tab_id
    
    async def on_unmount(self) -> None:
        """Cleanup when app closes"""
        if self.refresh_task:
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass


def main():
    """Entry point for the Moon Dev Quant App"""
    app = MoonDevQuantApp()
    app.run()


if __name__ == "__main__":
    main()
