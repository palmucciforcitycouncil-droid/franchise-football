# Start Trade Testing - Manual Instructions

## Quick Status Check ✅
- **Backend:** Needs to be started manually
- **Frontend:** Needs to be started manually  
- **Status:** All code pushed to `docs/gdd-v3-2` branch
- **Integration:** 100% complete

## 🚀 Manual Start Commands

### Terminal 1: Start Backend
```bash
# In project root directory
uvicorn app.ui.api:app --reload --port 8000
```

Expected output: `INFO: Uvicorn running on http://127.0.0.1:8000`

### Terminal 2: Start Frontend  
```bash
# Change to frontend directory
cd app/ui/figma-v2

# Start dev server
npm run dev
```

Expected output: Vite dev server URL (usually `http://localhost:5173`)

## 🧪 Quick Test

### 1. Verify Backend is Running
Open browser: `http://localhost:8000/docs`

You should see the FastAPI interactive documentation.

### 2. Test API Endpoint
Try this in browser: `http://localhost:8000/api/v1/teams/`

Should return JSON array of teams.

### 3. Open Frontend Trade Interface
- Open frontend URL (from npm output)
- Navigate to Trade section
- Select a team from dropdown
- Add assets to both sides
- Click "Submit Trade Offer"

## 📋 Testing Checklist

- [ ] Backend terminal shows no errors
- [ ] Frontend terminal shows no errors
- [ ] Teams dropdown populates with real data
- [ ] Selecting team loads their roster
- [ ] Draft picks display correctly
- [ ] Adding/removing assets works
- [ ] Submit trade shows success message
- [ ] Browser console shows no errors

## 🐛 If Backend Won't Start

### Check Python Environment
```bash
python --version
pip list | findstr uvicorn
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Check Database
```bash
# Make sure database is accessible
python -c "from app.models.database import engine; print('DB OK')"
```

## 🐛 If Frontend Won't Start

### Check Node.js
```bash
node --version
npm --version
```

### Install Dependencies
```bash
cd app/ui/figma-v2
npm install
```

## 📚 Reference Documents

- `QUICK_START.md` - Detailed testing guide
- `README_TRADE_ENGINE.md` - Architecture overview
- `TRADE_INTEGRATION_COMPLETE_FINAL.md` - Technical details
- `NEXT_SESSION_GUIDE.md` - Next steps

## ✅ Expected Results

Once everything is running:
1. **Backend:** Responding on http://localhost:8000
2. **Frontend:** Showing on http://localhost:5173 (or similar)
3. **Trade Interface:** Fully functional with real data
4. **Console:** No errors in browser or terminal

## 🎯 Next Steps After Testing

1. Run through full trade flow
2. Document any bugs found
3. Test error scenarios
4. Verify data persistence
5. Check database for trade proposals

---

**Ready to test?** Follow the manual commands above! 🚀
