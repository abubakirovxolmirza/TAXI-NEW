# Pricing Delete Endpoints - Quick Reference

## New Endpoints Added

### 1. Delete Pricing by ID
- **Method:** `DELETE`
- **URL:** `/api/admin/pricing/{pricing_id}`
- **Auth:** Admin or SuperAdmin
- **Description:** Delete a specific pricing record by ID

**Example:**
```
DELETE http://localhost:8000/api/admin/pricing/5
Authorization: Bearer {your_admin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "Pricing with ID 5 deleted successfully"
}
```

---

### 2. Delete All Pricing
- **Method:** `DELETE`
- **URL:** `/api/admin/pricing`
- **Auth:** SuperAdmin ONLY
- **Description:** Delete ALL pricing records from database

⚠️ **WARNING:** This action is irreversible!

**Example:**
```
DELETE http://localhost:8000/api/admin/pricing
Authorization: Bearer {your_superadmin_token}
```

**Response:**
```json
{
  "success": true,
  "message": "All pricing deleted successfully. Total deleted: 15"
}
```

---

## CLI Scripts Available

### Quick Delete All
```bash
python scripts/delete_all_pricing.py
```

### Interactive Delete Tool
```bash
python scripts/delete_pricing.py
```

See `PRICING_DELETE_GUIDE.md` for detailed documentation.
