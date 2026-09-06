# Quick Start Guide - Trade Engine Testing

## Prerequisites
- Python 3.9+ installed
- Node.js 16+ installed
- Database running (if applicable)

## 🚀 Quick Start (3 Steps)

### 1. Start the Backend
```bash
# In the project root
uvicorn app.ui.api:app --reload --port 8000
```
Backend will be available at: `http://localhost:8000`

### 2. Start the Frontend
```bash
# Navigate to frontend directory
cd app/ui/figma-v2

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```
Frontend will be available at: `http://localhost:5173` (or similar)

### 3. Test the Trade Flow

1. **Navigate to Trade Interface**
   - Open your browser to the frontend URL
   - Find the Trade section in the GM dashboard

2. **Select a Team**
   - Use the dropdown to select a trade partner
   - Wait for their roster and picks to load

3. **Add Assets**
   - Add players/picks to "You Offer" section
   - Add players/picks to "You Receive" section

4. **Submit Trade**
   - Click "Submit Trade Offer"
   - Check console for API response
   - Verify success/error message appears

## 🧪 API Testing (Optional)

### Test Backend Directly

**Get All Teams:**
```bash
curl http://localhost:8000/api/v1/teams/
```

**Get Team Roster:**
```bash
curl http://localhost:8000/api/v1/teams/1/roster?season=2025
```

**Get Team Picks:**
```bash
curl http://localhost:8000/api/v1/teams/1/picks?season=2025
```

**Get Season Context:**
```bash
curl http://localhost:8000/api/v1/season/current
```

**Submit Trade (Example):**
```bash
curl -X POST http://localhost:8000/api/v1/trades/propose \
  -H "Content-Type: application/json" \
  -d '{
    "season": 2025,
    "from_team_id": 1,
    "to_team_id": 2,
    "from_assets": {
      "players": [1],
      "picks": [{"round": 1, "slot": 10}]
    },
    "to_assets": {
      "players": [10],
      "picks": [{"round": 2, "slot": 20}]
    }
  }'
```

## 📋 Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Teams dropdown populates with data
- [ ] Selecting a team loads their roster
- [ ] Draft picks display correctly
- [ ] Player cards show correct information
- [ ] Adding assets works smoothly
- [ ] Removing assets works correctly
- [ ] Submit button sends request to backend
- [ ] Success message displays on completion
- [ ] Error handling works for invalid trades
- [ ] Form clears after submission

## 🐛 Troubleshooting

### Backend Issues
- **Port already in use**: Change port with `--port 8001`
- **Import errors**: Run `pip install -r requirements.txt`
- **Database errors**: Check database connection string

### Frontend Issues
- **404 on API calls**: Check API_BASE URL in `tradeApi.ts`
- **CORS errors**: Add CORS middleware to backend
- **Type errors**: Run `npm run type-check`

### Data Issues
- **Empty teams list**: Check database has team data
- **No players loading**: Verify roster data exists
- **Pick numbers missing**: Check draft pick inventory

## 🔍 Debugging Tips

### Enable API Logging
Add to FastAPI startup:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Frontend Console
Open browser DevTools (F12):
- Check Console tab for errors
- Check Network tab for API calls
- Verify request/response payloads

### Backend Logs
Watch terminal output:
- API request logs
- Database queries
- Error stack traces

## 📞 Need Help?

1. Check the browser console for errors
2. Check the backend terminal for errors
3. Verify database has test data
4. Review `TRADE_INTEGRATION_COMPLETE_FINAL.md` for details

## 🎉 Success Indicators

You'll know it's working when:
- ✅ No errors in console
- ✅ Team roster loads instantly
- ✅ Trade submission shows success message
- ✅ Backend logs show 200 OK responses
- ✅ Data persists in database

**Happy Trading!** 🏈
