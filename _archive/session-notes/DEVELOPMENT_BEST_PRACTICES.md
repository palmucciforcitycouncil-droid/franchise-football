# Franchise Football - Development Best Practices

## 🚀 Quick Start

### 1. Setup Development Environment
```powershell
.\setup_dev.ps1
```

### 2. Start Server
```powershell
.\server.ps1 start
```

### 3. Check Status
```powershell
.\server.ps1 status
```

### 4. Run Tests
```powershell
.\test_runner.ps1
```

## 📁 Directory Structure

```
franchise-football/
├── app/                    # FastAPI application
├── project_config.ps1     # Project configuration
├── server.ps1             # Server management
├── setup_dev.ps1          # Development setup
├── test_runner.ps1        # Test runner
└── README.md              # This file
```

## 🔧 Server Management

### Available Commands
- `.\server.ps1 start` - Start server in background
- `.\server.ps1 stop` - Stop server
- `.\server.ps1 restart` - Restart server
- `.\server.ps1 status` - Check server status
- `.\server.ps1 logs` - Show logs (foreground only)

### Environment Variables
- `USE_PBP_V2` - Enable/disable PBP v2 (default: false)
- `HFA_POINTS` - Home field advantage points (default: 1.4)
- `LEAGUE_SEED` - Random seed for deterministic results (default: 101)

## 🧪 Testing

### Test Types
- `.\test_runner.ps1 server` - Test server endpoints
- `.\test_runner.ps1 schedule` - Test schedule generation
- `.\test_runner.ps1 simulation` - Test simulation flow
- `.\test_runner.ps1 rng` - Test RNG validation
- `.\test_runner.ps1 all` - Run all tests

## 🎯 Best Practices

### 1. Always Use Project Root
```powershell
# ❌ Wrong - from subdirectory
cd "C:\Users\bpalm\Documents\franchise-football\app\ui\figma\dashboard-vite\src"
py -m uvicorn app.main:app --host 127.0.0.1 --port 8011

# ✅ Correct - from project root
cd "C:\Users\bpalm\Documents\franchise-football"
py -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

### 2. Use Server Management Script
```powershell
# ❌ Manual server management
py -m uvicorn app.main:app --host 127.0.0.1 --port 8011

# ✅ Use server script
.\server.ps1 start
```

### 3. Check Server Status Before Testing
```powershell
# Always check if server is running
.\server.ps1 status

# Or test manually
Invoke-WebRequest -Uri "http://127.0.0.1:8011/" -Method GET
```

### 4. Use Environment Setup
```powershell
# ❌ Manual environment setup
$env:USE_PBP_V2 = "false"
$env:HFA_POINTS = "1.4"
py -m uvicorn app.main:app --host 127.0.0.1 --port 8011

# ✅ Use setup script
.\setup_dev.ps1
.\server.ps1 start
```

## 🚨 Common Issues & Solutions

### Issue: "Could not import module 'app.main'"
**Cause**: Starting server from wrong directory
**Solution**: 
```powershell
cd "C:\Users\bpalm\Documents\franchise-football"
.\server.ps1 start
```

### Issue: Server not responding
**Cause**: Server not running or crashed
**Solution**:
```powershell
.\server.ps1 status
.\server.ps1 restart
```

### Issue: Port already in use
**Cause**: Another server instance running
**Solution**:
```powershell
.\server.ps1 stop
.\server.ps1 start
```

## 🔄 Workflow

### Daily Development
1. `.\setup_dev.ps1` - Setup environment
2. `.\server.ps1 start` - Start server
3. Make code changes
4. `.\test_runner.ps1` - Test changes
5. `.\server.ps1 restart` - Restart if needed

### Testing
1. `.\server.ps1 status` - Verify server running
2. `.\test_runner.ps1 all` - Run all tests
3. Check results and fix issues

### Debugging
1. `.\server.ps1 stop` - Stop background server
2. `.\server.ps1 start -Background:$false` - Start in foreground to see logs
3. Debug issues
4. `.\server.ps1 start` - Restart in background

## 📚 Additional Resources

- API Documentation: http://127.0.0.1:8011/docs
- Server Health: http://127.0.0.1:8011/
- Project Root: `C:\Users\bpalm\Documents\franchise-football`
