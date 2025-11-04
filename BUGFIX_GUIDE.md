# Critical API Bug Fix Guide

**Priority:** 🚨 **URGENT** - Must fix before deployment
**Date Discovered:** October 29, 2025
**Discovered By:** Integration tests (Phase 7.1)

---

## Quick Reference

**3 Critical Bugs** requiring immediate fixes in `backend/api/routes.py`:

| Bug | Severity | Lines | Fix Time |
|-----|----------|-------|----------|
| #1: Portfolio field naming | CRITICAL | 124-125, 260-284 | 5 min |
| #2: MarketDataService init | CRITICAL | 381 | 2 min |
| #3: API field standardization | HIGH | Multiple | 10 min |

**Total estimated fix time:** ~20 minutes

---

## Bug #1: Portfolio Endpoint Field Naming

### Location
`backend/api/routes.py` - Lines 124-125, 260-284

### Problem
```python
# BROKEN CODE:
"total_pl_pct": decimal_to_float(portfolio.total_pl_pct),  # Field doesn't exist!
"realized_pl": decimal_to_float(portfolio.realized_pl),    # Field doesn't exist!
```

### Why It Fails
- Portfolio model uses `total_pl_percentage` not `total_pl_pct`
- Portfolio model has NO `realized_pl` field
- **Error:** `AttributeError: 'Portfolio' object has no attribute 'total_pl_pct'`

### Fix Option 1: Match Existing Model (RECOMMENDED)
```python
# Line 124 - Change this:
"total_pl_pct": decimal_to_float(portfolio.total_pl_pct),

# To this:
"total_pl_pct": decimal_to_float(portfolio.total_pl_percentage),

# Line 125 - Remove this line entirely:
"realized_pl": decimal_to_float(portfolio.realized_pl),
```

### Fix Option 2: Add Fields to Model (NOT RECOMMENDED)
Alternatively, add fields to `backend/models/portfolio.py`:
```python
# Add these to Portfolio model:
total_pl_pct = Column(Float, nullable=False, default=0.0)  # Alias for percentage
realized_pl = Column(Float, nullable=False, default=0.0)   # Track realized P&L

# Then run migration:
alembic revision --autogenerate -m "Add total_pl_pct and realized_pl to portfolio"
alembic upgrade head
```

**Recommendation:** Use Fix Option 1 (simpler, no migration needed)

### All Occurrences to Fix
Search for `total_pl_pct` and `realized_pl` in `backend/api/routes.py`:
- Line 124: `get_portfolio()` endpoint
- Line 125: `get_portfolio()` endpoint
- Lines 260-284: `get_performance()` endpoint

---

## Bug #2: MarketDataService Initialization

### Location
`backend/api/routes.py` - Line 381

### Problem
```python
# BROKEN CODE (line 381):
market_data = MarketDataService()  # Missing required 'db' parameter!
```

### Why It Fails
`MarketDataService.__init__()` requires a `db` parameter:
```python
# From backend/services/market_data.py:
def __init__(self, db: Session):
    self.db = db
    # ...
```

**Error:** `TypeError: MarketDataService.__init__() missing 1 required positional argument: 'db'`

### Fix
```python
# Line 373-406: Update get_market_status() function
@router.get("/market/status", response_model=Dict[str, Any])
async def get_market_status(db: Session = Depends(get_db)):  # ADD db parameter
    """Get current market status"""
    market_data = MarketDataService(db)  # PASS db to constructor

    try:
        is_open = market_data.is_market_open()
        # ... rest of code unchanged
```

**Changes:**
1. Add `db: Session = Depends(get_db)` to function signature
2. Pass `db` to `MarketDataService(db)`

---

## Bug #3: API Field Naming Standardization

### Location
Multiple locations in `backend/api/routes.py`

### Problem
API returns field names that don't match database model field names:

| API Field | Model Field | Status |
|-----------|-------------|--------|
| `total_pl_pct` | `total_pl_percentage` | ❌ Mismatch |
| `unrealized_pl_pct` | `unrealized_pl_percentage` | ❌ Mismatch |
| `realized_pl` | (doesn't exist) | ❌ Missing |

### Why It Matters
- Frontend expects API field names to be consistent
- Current mismatches cause display errors
- Developers get confused about correct field names

### Fix Strategy

**Option 1: Change API to Match Models (RECOMMENDED)**
Update all API endpoints to use model field names:
```python
# Change all occurrences:
"total_pl_pct" → "total_pl_percentage"
"unrealized_pl_pct" → "unrealized_pl_percentage"
```

**Option 2: Use Serializers/DTOs**
Create Pydantic response models that map model fields to API fields:
```python
from pydantic import BaseModel, Field

class PortfolioResponse(BaseModel):
    total_pl_pct: float = Field(alias="total_pl_percentage")
    # ... other fields
```

**Recommendation:** Use Option 1 for simplicity

### Files to Audit
Search for `_pct` in these files:
- `backend/api/routes.py` - All endpoint return dictionaries
- `frontend/src/api.ts` - API client (may need updates)
- `frontend/src/types.ts` - TypeScript interfaces (may need updates)

---

## Verification Steps

### 1. Run Integration Tests
```bash
# From project root:
pytest tests/test_api_integration.py -v

# Expected result:
# 17 passed, 0 failed (100% pass rate)
```

### 2. Manual API Testing
```bash
# Start backend:
uvicorn backend.main:app --reload

# Test endpoints:
curl http://localhost:8000/api/models/1/portfolio
curl http://localhost:8000/api/market/status
curl http://localhost:8000/api/leaderboard
```

### 3. Frontend Testing
```bash
# Start frontend:
cd frontend && npm run dev

# Visit: http://localhost:3000
# Check: Dashboard, portfolio data, market status all display correctly
```

### 4. Update Documentation
- [ ] Mark bugs as fixed in [TASKS.md Phase 7.0](TASKS.md)
- [ ] Update [PHASE_7.1_API_TESTS.md](PHASE_7.1_API_TESTS.md) with test results
- [ ] Update [README.md](README.md) status to "Production Ready"

---

## Complete Fix Checklist

- [ ] **Bug #1: Portfolio Field Naming**
  - [ ] Line 124: Change `portfolio.total_pl_pct` → `portfolio.total_pl_percentage`
  - [ ] Line 125: Remove `portfolio.realized_pl` line
  - [ ] Lines 260-284: Fix same issues in `get_performance()`

- [ ] **Bug #2: MarketDataService Init**
  - [ ] Line 373: Add `db: Session = Depends(get_db)` parameter
  - [ ] Line 381: Change `MarketDataService()` → `MarketDataService(db)`

- [ ] **Bug #3: Field Name Standardization**
  - [ ] Search and replace `"total_pl_pct"` → `"total_pl_percentage"` in API responses
  - [ ] Search and replace `"unrealized_pl_pct"` → `"unrealized_pl_percentage"` in API responses
  - [ ] Verify frontend still works (or update frontend types)

- [ ] **Verification**
  - [ ] Run: `pytest tests/test_api_integration.py -v` (17/17 passing)
  - [ ] Test API manually with curl
  - [ ] Test frontend in browser
  - [ ] Update documentation

---

## After Fixes Complete

1. **Update Status:**
   - Change README.md status from "CRITICAL BUGS" to "PRODUCTION READY"
   - Mark Phase 7.0 as complete in TASKS.md
   - Update PHASE_7.1_API_TESTS.md with 100% pass rate

2. **Proceed with Deployment:**
   - ✅ Safe to run 1-week local evaluation
   - ✅ Safe to deploy to Raspberry Pi
   - ✅ Safe to share with users

---

## Questions?

**Q: Can I deploy before fixing these bugs?**
A: ❌ NO! These bugs will cause API crashes in production.

**Q: Which bug should I fix first?**
A: Fix in order: Bug #2 (fastest) → Bug #1 → Bug #3

**Q: Do I need to update the frontend?**
A: Maybe. If you use Option 1 for Bug #3, frontend might need updates to expect `*_percentage` fields.

**Q: How do I know if bugs are fixed?**
A: Run integration tests - they'll pass if bugs are fixed.

---

**Created:** October 29, 2025
**Author:** Claude Code Integration Tests
**Priority:** URGENT - Fix before any deployment
