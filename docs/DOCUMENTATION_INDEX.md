# Documentation Index

This project contains comprehensive documentation for all components and features. Use this index to find the right documentation for your needs.

## 📚 Core Documentation

### **CLAUDE.md** - Main Development Guide
- Primary Claude Code guidance document
- Project structure and architecture overview
- Setup instructions and common commands
- Unicode handling and Windows compatibility
- Integration patterns and best practices

### **QUICKSTART.md** - Quick Setup Guide
- Fast-track setup for new developers
- Essential configuration steps
- Basic usage examples
- Safety checklist reference

## 🔧 Feature-Specific Documentation

### **CLAUDE_DIP_BUY.md** - Dip Buying Strategy (v2.0)
- **Comprehensive guide** for the advanced dip buying feature
- Architecture and component overview
- Configuration reference with all parameters
- State management and persistence details
- **Recent bug fixes** and production readiness notes
- Debugging guide with validation error messages
- Thread safety and performance considerations

### **SIMULATOR_ARCHITECTURE.md** - Trading Strategy Simulator
- Complete simulator architecture overview
- Historical backtesting capabilities
- Performance analysis and reporting
- Configuration options and best practices
- Integration with dip buying strategy

### **CLAUDE_SIMULATOR.md** - Detailed Simulator Guide
- Step-by-step simulator usage
- Strategy testing methodologies
- Result interpretation guidelines
- Advanced configuration options

## 🔧 Technical References

### **BITVAVO_API_UPDATE.md** - API Changes
- Recent Bitvavo API updates and requirements
- operatorId parameter implementation
- Breaking changes and migration guide
- Error handling patterns

### **GIT_WORKFLOW.md** - Development Workflow
- Git branching strategy
- Commit message standards
- Code review process
- Release management

### **SAFETY_CHECKLIST.md** - Pre-Trading Safety
- Essential safety checks before live trading
- Configuration validation steps
- Risk management guidelines
- Emergency procedures

## 📝 Usage Documentation

### **FIRST_RUN_BEHAVIOR.md** - Initial Setup
- What to expect on first run
- Common initial issues and solutions
- Configuration validation process
- State initialization behavior

### **TERMINAL_OUTPUT_EXAMPLE.md** - Expected Output
- Example terminal output during operation
- Log message interpretation
- Status indicators and their meanings
- Error message patterns

## 📂 Directory-Specific Guides

### **data/README.md** - Data Persistence
- Data directory structure
- File format specifications
- Backup and recovery procedures
- Persistence patterns

### **logs/README.md** - Logging System
- Log file organization
- Log level descriptions
- Debugging with log analysis
- Log rotation and maintenance

## 🧪 Testing Documentation

### Test Files
- `test_simulator.py` - Comprehensive simulator tests
- `test_simulator_simple.py` - Basic functionality validation
- `tests/` directory - Unit test suite with pytest configuration

### Testing Patterns
- Mock API usage for safe testing
- Configuration testing approaches
- Integration testing strategies
- Performance benchmarking methods

## 📊 Configuration Reference

### Environment Variables
- **Core Trading**: API keys, trade amounts, intervals
- **Dip Buying**: Multi-level configuration, timing parameters
- **System**: Logging levels, rate limits, timeouts
- **Optional**: Market filtering, advanced features

### Configuration Files
- `.env.example` - Template with all available options
- `pytest.ini` - Test configuration
- `setup.py` - Package configuration

## 🔄 Recent Updates (v2.0)

### Major Improvements
1. **Thread Safety** - All components now thread-safe with atomic operations
2. **API Compliance** - Full Bitvavo API compatibility verified
3. **Input Validation** - Comprehensive validation with graceful error handling
4. **Performance** - Optimized for production use with robust error recovery
5. **Documentation** - Updated with all recent changes and best practices

### Breaking Changes
- DipBuyManager constructor now requires `trading_config` parameter
- State management uses atomic writes (may require file permission updates)
- Python 3.8+ compatibility (updated type hints)

## 🚀 Getting Started Workflow

1. **New Developers**: Start with `QUICKSTART.md`
2. **Dip Buying Feature**: Read `CLAUDE_DIP_BUY.md` for comprehensive guide
3. **Strategy Testing**: Use `SIMULATOR_ARCHITECTURE.md` for backtesting
4. **Production Deployment**: Follow `SAFETY_CHECKLIST.md`
5. **Development Work**: Reference `CLAUDE.md` for architecture details

## 📞 Support and Troubleshooting

### Common Issues
- **Unicode Errors**: See Unicode section in `CLAUDE.md`
- **Dip Strategy Issues**: Check validation errors in `CLAUDE_DIP_BUY.md`
- **Simulator Problems**: Reference `SIMULATOR_ARCHITECTURE.md`
- **API Errors**: Review `BITVAVO_API_UPDATE.md`

### Debug Resources
- Log message patterns in component-specific guides
- Validation error explanations in feature documentation
- Performance troubleshooting in architecture guides

This documentation is actively maintained and reflects the current state of the codebase. All guides are updated with the latest v2.0 improvements including critical bug fixes, thread safety enhancements, and production readiness features.