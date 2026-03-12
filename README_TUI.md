# Moon Dev Quant App TUI

A comprehensive terminal-based trading interface for cryptocurrency quantitative trading with live data feeds, system monitoring, and prediction market integration.

## 🌙 Features

### Live Data Panels
- **BTC Ticker**: Real-time Bitcoin price with 24h change
- **Hyperliquid Funding Scanner**: Top 30 most negative funding rates
- **Guardian Agent Memory Monitor**: Process memory leak detection with 30s refresh
- **Top Non-Python Processes**: System resource monitoring
- **Polymarket Bots**: Prediction market signals and analysis

### Four Main Tabs
1. **Trade**: Live trading interface with positions and quick actions
2. **Code**: Strategy code editor and management
3. **Backtest**: Backtesting engine with performance metrics
4. **Data**: System monitoring and data feeds

### Key Features
- **Auto-refresh**: All panels update every 30 seconds
- **Bypass Permissions**: Shift+Tab for advanced operations
- **Colorful Rich/Textual UI**: Professional terminal interface
- **Live API Integration**: Real data from Hyperliquid and Polymarket
- **Memory Leak Detection**: Guardian agent monitors process growth
- **Keyboard Shortcuts**: Fast navigation and control

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Windows/Linux/macOS terminal
- Internet connection for live data

### Installation

1. **Clone or download the files**:
   ```bash
   # Ensure you have these files:
   # - moon_dev_tui.py
   # - hyperliquid_api.py
   # - polymarket_api.py
   # - requirements_tui.txt
   # - run_moon_dev_tui.py
   ```

2. **Run the launcher** (handles installation automatically):
   ```bash
   python run_moon_dev_tui.py
   ```

   Or install manually:
   ```bash
   pip install -r requirements_tui.txt
   python moon_dev_tui.py
   ```

### First Run
The launcher will:
- ✅ Check Python version compatibility
- 📦 Install required dependencies automatically
- 🔍 Verify all modules are available
- 📝 Create configuration files
- 🚀 Launch the TUI application

## 🎮 Controls

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `F1` or `1` | Switch to Trade tab |
| `F2` or `2` | Switch to Code tab |
| `F3` or `3` | Switch to Backtest tab |
| `F4` or `4` | Switch to Data tab |
| `Shift+Tab` | Toggle bypass permissions |
| `R` | Manual refresh all data |
| `Q` | Quit application |

### Navigation
- Use arrow keys to navigate between panels
- Tab to cycle through interactive elements
- Enter to activate buttons/selections

## 📊 Panel Details

### BTC Ticker
- Live Bitcoin price from market data
- 24-hour percentage change with color coding
- Volume information
- Live indicator (green dot)

### Hyperliquid Funding Scanner
- Top 30 most negative funding rates
- Real-time data from Hyperliquid API
- Open interest values
- Next funding payment countdown
- Auto-refresh every 30 seconds

### Guardian Agent Memory Monitor
- Tracks memory usage of all processes
- Detects memory leaks (>50MB growth = LEAK)
- Color-coded status: OK (green), WARN (yellow), LEAK (red)
- Refreshes every 30 seconds
- Shows PID, memory usage, and growth rate

### Top Non-Python Processes
- System processes excluding Python
- CPU usage percentage with color coding
- Memory consumption
- Thread count
- Sorted by CPU usage

### Polymarket Bots
- Live prediction market data
- Trading signals: LONG, SHORT, NEUTRAL
- Market volume and Yes percentage
- Automated bot strategy analysis

### Active Positions
- Real-time trading positions
- PnL tracking with color coding
- Portfolio summary
- Margin usage monitoring

## 🔧 Configuration

### Environment Variables
Create a `.env` file with:
```bash
# API Configuration
HYPERLIQUID_API_TIMEOUT=30
POLYMARKET_API_TIMEOUT=30

# Refresh Settings
REFRESH_INTERVAL=30
MEMORY_LEAK_THRESHOLD=50

# Debug Mode
MOON_DEV_TUI_DEBUG=false
```

### API Integration
The TUI integrates with:
- **Hyperliquid Data Layer API**: For funding rates and perpetual data
- **Polymarket API**: For prediction market data
- **System APIs**: For process monitoring via psutil

## 🛠️ Development

### Project Structure
```
moon-dev-quant-tui/
├── moon_dev_tui.py          # Main TUI application
├── hyperliquid_api.py       # Hyperliquid API client
├── polymarket_api.py        # Polymarket API client
├── requirements_tui.txt     # Python dependencies
├── run_moon_dev_tui.py      # Launcher script
└── README_TUI.md           # This file
```

### Dependencies
- **textual**: Modern TUI framework
- **rich**: Rich text and formatting
- **aiohttp**: Async HTTP client
- **psutil**: System process monitoring
- **asyncio**: Async programming support

### Adding New Panels
1. Create a new class inheriting from `Static`
2. Implement the `render()` method returning a `RichTable`
3. Add to the appropriate tab in `compose()`
4. Update `refresh_data()` method if needed

### API Integration
Each API client follows the async context manager pattern:
```python
async with HyperliquidAPI() as api:
    data = await api.get_funding_rates()
```

## 🐛 Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Run the launcher to auto-install dependencies
python run_moon_dev_tui.py
```

**API Connection Issues**:
- Check internet connection
- Verify API endpoints are accessible
- Check firewall settings

**Performance Issues**:
- Reduce refresh interval in settings
- Close other resource-intensive applications
- Check system memory usage

**Display Issues**:
- Ensure terminal supports colors
- Try different terminal emulators
- Adjust terminal size (minimum 120x40 recommended)

### Debug Mode
Enable debug mode for detailed logging:
```bash
export MOON_DEV_TUI_DEBUG=true
python moon_dev_tui.py
```

## 📈 Features Roadmap

### Planned Features
- [ ] Real-time WebSocket connections
- [ ] Advanced charting with candlesticks
- [ ] Strategy backtesting integration
- [ ] Alert system with notifications
- [ ] Portfolio optimization tools
- [ ] Risk management dashboard
- [ ] Multi-exchange support
- [ ] Custom indicator development

### API Integrations
- [ ] Binance API integration
- [ ] CoinGecko price feeds
- [ ] DeFiLlama protocol data
- [ ] Twitter sentiment analysis
- [ ] News feed integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the Moon Dev AI Agents repository and follows the same licensing terms.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the GitHub issues
3. Create a new issue with detailed information

---

**Moon Dev Quant TUI v2.1.0** - Professional crypto trading terminal interface