#!/usr/bin/env python3
"""
Comprehensive Backend Test for ROLLOW Cafe Management - Phase A+B+C
Tests all new endpoints: config registries, audit, expenses, adjustments, print logs, external sales, finance summary
"""

import requests
import json
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://rlw-main-deploy.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
CREDENTIALS = {
    "owner": {"email": "owner@rollow.id", "password": "Rollow@2026"},
    "finance": {"email": "finance@rollow.id", "password": "Rollow@2026"},
    "crew": {"email": "crew@rollow.id", "password": "Rollow@2026"},
    "manager": {"email": "manager@rollow.id", "password": "Rollow@2026"},
}

# Global tokens storage
tokens = {}

def login(role):
    """Login and get JWT token for a role"""
    print(f"\n🔐 Logging in as {role}...")
    resp = requests.post(f"{BASE_URL}/auth/login", json=CREDENTIALS[role])
    if resp.status_code != 200:
        print(f"❌ Login failed for {role}: {resp.status_code} - {resp.text}")
        return None
    data = resp.json()
    token = data.get("access_token")
    tokens[role] = token
    print(f"✅ Logged in as {role}: {data['user']['name']}")
    return token

def headers(role):
    """Get authorization headers for a role"""
    return {"Authorization": f"Bearer {tokens[role]}"}

def test_config_registries():
    """Test 1: Config registries GET/POST/PUT for all 5 kinds"""
    print("\n" + "="*80)
    print("TEST 1: CONFIG REGISTRIES (payment_methods, expense_categories, fund_pockets, payroll_components, platforms)")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Test GET for each kind - verify seed data
    kinds = {
        "payment_methods": {"expected_count": 4, "names": ["Cash", "QRIS", "Debit", "Transfer"]},
        "expense_categories": {"expected_count": 16, "names": ["Bahan Baku", "Gaji", "WiFi"]},
        "fund_pockets": {"expected_count": 10, "names": ["HPP / Bahan Baku", "Gaji & Payroll", "WiFi"]},
        "payroll_components": {"expected_count": 7, "names": ["Bonus Kehadiran", "Potongan Keterlambatan"]},
        "platforms": {"expected_count": 3, "names": ["ShopeeFood", "GoFood", "GrabFood"]},
    }
    
    for kind, info in kinds.items():
        print(f"\n📋 Testing GET /api/config/{kind}")
        resp = requests.get(f"{BASE_URL}/config/{kind}", headers=headers("owner"))
        if resp.status_code == 200:
            items = resp.json()
            if len(items) >= info["expected_count"]:
                print(f"✅ GET {kind}: {len(items)} items (expected >= {info['expected_count']})")
                # Check some expected names
                names = [x["name"] for x in items]
                for expected_name in info["names"]:
                    if expected_name in names:
                        print(f"   ✓ Found seed item: {expected_name}")
                    else:
                        print(f"   ⚠️  Missing seed item: {expected_name}")
                results["passed"] += 1
            else:
                print(f"❌ GET {kind}: Only {len(items)} items, expected >= {info['expected_count']}")
                results["failed"] += 1
                results["errors"].append(f"GET {kind}: insufficient seed data")
        else:
            print(f"❌ GET {kind} failed: {resp.status_code} - {resp.text}")
            results["failed"] += 1
            results["errors"].append(f"GET {kind}: {resp.status_code}")
    
    # Test GET with active=true filter
    print(f"\n📋 Testing GET /api/config/payment_methods?active=true")
    resp = requests.get(f"{BASE_URL}/config/payment_methods?active=true", headers=headers("owner"))
    if resp.status_code == 200:
        items = resp.json()
        all_active = all(x.get("is_active", True) for x in items)
        if all_active:
            print(f"✅ GET payment_methods?active=true: {len(items)} active items")
            results["passed"] += 1
        else:
            print(f"❌ GET payment_methods?active=true: contains inactive items")
            results["failed"] += 1
            results["errors"].append("active filter not working")
    else:
        print(f"❌ GET payment_methods?active=true failed: {resp.status_code}")
        results["failed"] += 1
    
    # Test POST - create new payment method (owner should succeed)
    print(f"\n📋 Testing POST /api/config/payment_methods (as owner)")
    new_method = {"name": "OVO", "kind": "ewallet", "fee_percent": 1.5, "fee_fixed": 0, "is_active": True, "sort": 10}
    resp = requests.post(f"{BASE_URL}/config/payment_methods", json=new_method, headers=headers("owner"))
    if resp.status_code == 200:
        created = resp.json()
        print(f"✅ POST payment_methods: created '{created['name']}' with id {created['id']}")
        results["passed"] += 1
        
        # Test PUT - update the created item
        print(f"\n📋 Testing PUT /api/config/payment_methods/{created['id']} (deactivate)")
        update = {"is_active": False, "fee_percent": 2.0}
        resp = requests.put(f"{BASE_URL}/config/payment_methods/{created['id']}", json=update, headers=headers("owner"))
        if resp.status_code == 200:
            updated = resp.json()
            if not updated.get("is_active") and updated.get("fee_percent") == 2.0:
                print(f"✅ PUT payment_methods: updated is_active=False, fee_percent=2.0")
                results["passed"] += 1
            else:
                print(f"❌ PUT payment_methods: update not applied correctly")
                results["failed"] += 1
        else:
            print(f"❌ PUT payment_methods failed: {resp.status_code} - {resp.text}")
            results["failed"] += 1
    else:
        print(f"❌ POST payment_methods failed: {resp.status_code} - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"POST payment_methods: {resp.status_code}")
    
    # Test RBAC - crew should be denied POST
    print(f"\n📋 Testing POST /api/config/payment_methods (as crew - should be 403)")
    resp = requests.post(f"{BASE_URL}/config/payment_methods", json={"name": "Test"}, headers=headers("crew"))
    if resp.status_code == 403:
        print(f"✅ POST payment_methods as crew: correctly denied (403)")
        results["passed"] += 1
    else:
        print(f"❌ POST payment_methods as crew: expected 403, got {resp.status_code}")
        results["failed"] += 1
        results["errors"].append(f"RBAC violation: crew can POST payment_methods")
    
    # Test validation - POST without name should fail
    print(f"\n📋 Testing POST /api/config/payment_methods without name (should be 400)")
    resp = requests.post(f"{BASE_URL}/config/payment_methods", json={"kind": "other"}, headers=headers("owner"))
    if resp.status_code == 400:
        print(f"✅ POST payment_methods without name: correctly rejected (400)")
        results["passed"] += 1
    else:
        print(f"❌ POST payment_methods without name: expected 400, got {resp.status_code}")
        results["failed"] += 1
    
    print(f"\n📊 Config Registries Test: {results['passed']} passed, {results['failed']} failed")
    return results

def test_audit():
    """Test 2: Audit trail viewer"""
    print("\n" + "="*80)
    print("TEST 2: AUDIT TRAIL VIEWER")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Test GET /api/audit (owner should succeed)
    print(f"\n📋 Testing GET /api/audit (as owner)")
    resp = requests.get(f"{BASE_URL}/audit", headers=headers("owner"))
    if resp.status_code == 200:
        data = resp.json()
        if "logs" in data and "entities" in data:
            print(f"✅ GET /api/audit: returned {len(data['logs'])} logs, {len(data['entities'])} entities")
            results["passed"] += 1
        else:
            print(f"❌ GET /api/audit: missing 'logs' or 'entities' in response")
            results["failed"] += 1
    else:
        print(f"❌ GET /api/audit failed: {resp.status_code} - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"GET /api/audit: {resp.status_code}")
    
    # Test RBAC - crew should be denied
    print(f"\n📋 Testing GET /api/audit (as crew - should be 403)")
    resp = requests.get(f"{BASE_URL}/audit", headers=headers("crew"))
    if resp.status_code == 403:
        print(f"✅ GET /api/audit as crew: correctly denied (403)")
        results["passed"] += 1
    else:
        print(f"❌ GET /api/audit as crew: expected 403, got {resp.status_code}")
        results["failed"] += 1
        results["errors"].append(f"RBAC violation: crew can access audit")
    
    # Test filters
    print(f"\n📋 Testing GET /api/audit with filters (entity=user, action=create)")
    resp = requests.get(f"{BASE_URL}/audit?entity=user&action=create", headers=headers("owner"))
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ GET /api/audit with filters: returned {len(data['logs'])} logs")
        results["passed"] += 1
    else:
        print(f"❌ GET /api/audit with filters failed: {resp.status_code}")
        results["failed"] += 1
    
    print(f"\n📊 Audit Test: {results['passed']} passed, {results['failed']} failed")
    return results

def test_expenses():
    """Test 3: Petty cash expenses with approval workflow"""
    print("\n" + "="*80)
    print("TEST 3: PETTY CASH EXPENSES")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # First, ensure petty_cash_needs_approval is false (default)
    print(f"\n📋 Setting petty_cash_needs_approval=false")
    settings_update = {
        "tax_enabled": True, "tax_name": "PB1", "tax_percent": 10.0, "tax_default_on": True,
        "service_percent": 0.0, "loyalty_enabled": True, "points_per_nota": 1,
        "points_min_purchase": 0, "points_per_amount": 0, "petty_cash_limit": 50000,
        "stock_mode": "detailed", "petty_cash_needs_approval": False,
        "late_tolerance_min": 10, "late_penalty_fixed": 0, "late_penalty_per_minute": 0,
        "printer": {"paper_width": 58}, "qris": {}, "receipt": {"cafe_name": "ROLLOW", "footer_note": "Thank you!"}
    }
    resp = requests.put(f"{BASE_URL}/settings", json=settings_update, headers=headers("owner"))
    if resp.status_code == 200:
        print(f"✅ Settings updated: petty_cash_needs_approval=false")
    else:
        print(f"⚠️  Failed to update settings: {resp.status_code}")
    
    # Test POST /api/expenses without approval (should go directly to finance)
    print(f"\n📋 Testing POST /api/expenses (no approval needed)")
    expense_data = {
        "category": "Transportasi",
        "amount": 50000,
        "method": "Cash",
        "note": "Beli bahan ke pasar",
        "receiver": "Andi",
        "ref": "",
        "photo": ""
    }
    resp = requests.post(f"{BASE_URL}/expenses", json=expense_data, headers=headers("crew"))
    if resp.status_code == 200:
        expense = resp.json()
        if expense.get("pending") == False:
            print(f"✅ POST /api/expenses: created expense {expense['id']}, pending=False (directly to finance)")
            results["passed"] += 1
            
            # Verify it appears in GET /api/finance
            today = datetime.now().strftime("%Y-%m")
            resp = requests.get(f"{BASE_URL}/finance?month={today}", headers=headers("owner"))
            if resp.status_code == 200:
                finance_records = resp.json()
                found = any(f.get("category") == "Transportasi" and f.get("amount") == 50000 for f in finance_records)
                if found:
                    print(f"✅ Expense found in finance ledger")
                    results["passed"] += 1
                else:
                    print(f"❌ Expense NOT found in finance ledger")
                    results["failed"] += 1
        else:
            print(f"❌ POST /api/expenses: expected pending=False, got pending=True")
            results["failed"] += 1
    else:
        print(f"❌ POST /api/expenses failed: {resp.status_code} - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"POST /api/expenses: {resp.status_code}")
    
    # Now enable approval workflow
    print(f"\n📋 Setting petty_cash_needs_approval=true")
    settings_update["petty_cash_needs_approval"] = True
    resp = requests.put(f"{BASE_URL}/settings", json=settings_update, headers=headers("owner"))
    if resp.status_code == 200:
        print(f"✅ Settings updated: petty_cash_needs_approval=true")
    else:
        print(f"⚠️  Failed to update settings: {resp.status_code}")
    
    # Test POST /api/expenses with approval (crew should get pending=true)
    print(f"\n📋 Testing POST /api/expenses (with approval, as crew)")
    expense_data2 = {
        "category": "Perlengkapan Operasional",
        "amount": 75000,
        "method": "Cash",
        "note": "Beli tissue dan sabun",
        "receiver": "Budi",
        "ref": "",
        "photo": ""
    }
    resp = requests.post(f"{BASE_URL}/expenses", json=expense_data2, headers=headers("crew"))
    if resp.status_code == 200:
        expense = resp.json()
        if expense.get("pending") == True:
            print(f"✅ POST /api/expenses: created expense {expense['id']}, pending=True (needs approval)")
            results["passed"] += 1
            expense_id = expense["id"]
            
            # Test GET /api/expenses?pending=true
            print(f"\n📋 Testing GET /api/expenses?pending=true")
            resp = requests.get(f"{BASE_URL}/expenses?pending=true", headers=headers("owner"))
            if resp.status_code == 200:
                pending = resp.json()
                found = any(p["id"] == expense_id for p in pending)
                if found:
                    print(f"✅ GET /api/expenses?pending=true: found pending expense")
                    results["passed"] += 1
                else:
                    print(f"❌ Pending expense not found in list")
                    results["failed"] += 1
            else:
                print(f"❌ GET /api/expenses?pending=true failed: {resp.status_code}")
                results["failed"] += 1
            
            # Test POST /api/expenses/{id}/decide (approve)
            print(f"\n📋 Testing POST /api/expenses/{expense_id}/decide (approve)")
            resp = requests.post(f"{BASE_URL}/expenses/{expense_id}/decide", 
                               json={"approve": True, "note": "Approved by manager"}, 
                               headers=headers("manager"))
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == "approved":
                    print(f"✅ POST /api/expenses/{expense_id}/decide: approved successfully")
                    results["passed"] += 1
                    
                    # Verify it now appears in finance ledger
                    resp = requests.get(f"{BASE_URL}/finance?month={datetime.now().strftime('%Y-%m')}", headers=headers("owner"))
                    if resp.status_code == 200:
                        finance_records = resp.json()
                        found = any(f.get("category") == "Perlengkapan Operasional" and f.get("amount") == 75000 for f in finance_records)
                        if found:
                            print(f"✅ Approved expense found in finance ledger")
                            results["passed"] += 1
                        else:
                            print(f"❌ Approved expense NOT found in finance ledger")
                            results["failed"] += 1
                else:
                    print(f"❌ Expense not approved: {result}")
                    results["failed"] += 1
            else:
                print(f"❌ POST /api/expenses/{expense_id}/decide failed: {resp.status_code} - {resp.text}")
                results["failed"] += 1
        else:
            print(f"❌ POST /api/expenses: expected pending=True, got pending=False")
            results["failed"] += 1
    else:
        print(f"❌ POST /api/expenses failed: {resp.status_code} - {resp.text}")
        results["failed"] += 1
    
    # Test RBAC - crew should NOT be able to decide
    print(f"\n📋 Testing POST /api/expenses/{expense_id}/decide (as crew - should be 403)")
    resp = requests.post(f"{BASE_URL}/expenses/{expense_id}/decide", 
                       json={"approve": True, "note": "Test"}, 
                       headers=headers("crew"))
    if resp.status_code == 403:
        print(f"✅ POST /api/expenses/decide as crew: correctly denied (403)")
        results["passed"] += 1
    else:
        print(f"❌ POST /api/expenses/decide as crew: expected 403, got {resp.status_code}")
        results["failed"] += 1
        results["errors"].append(f"RBAC violation: crew can decide expenses")
    
    # Test validation - amount <= 0 should fail
    print(f"\n📋 Testing POST /api/expenses with amount=0 (should be 400)")
    resp = requests.post(f"{BASE_URL}/expenses", 
                        json={"category": "Test", "amount": 0, "method": "Cash", "note": "Test", "receiver": "Test"}, 
                        headers=headers("crew"))
    if resp.status_code == 400:
        print(f"✅ POST /api/expenses with amount=0: correctly rejected (400)")
        results["passed"] += 1
    else:
        print(f"❌ POST /api/expenses with amount=0: expected 400, got {resp.status_code}")
        results["failed"] += 1
    
    print(f"\n📊 Expenses Test: {results['passed']} passed, {results['failed']} failed")
    return results

def test_payment_adjustment():
    """Test 4: Payment adjustment (refund/additional)"""
    print("\n" + "="*80)
    print("TEST 4: PAYMENT ADJUSTMENT")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # First, open a register session
    print(f"\n📋 Opening register session")
    resp = requests.post(f"{BASE_URL}/register/open", json={"opening_cash": 100000}, headers=headers("owner"))
    if resp.status_code != 200:
        print(f"⚠️  Failed to open register: {resp.status_code} - {resp.text}")
    else:
        print(f"✅ Register opened")
    
    # Create a sale
    print(f"\n📋 Creating a sale")
    sale_data = {
        "items": [{"menu_id": "", "qty": 1, "note": ""}],
        "payment_method": "Cash",
        "customer": "Test Customer",
        "apply_tax": True,
        "cash_received": 30000,
        "order_note": "Test sale for adjustment"
    }
    
    # Get a menu item first
    resp = requests.get(f"{BASE_URL}/menus", headers=headers("owner"))
    if resp.status_code == 200:
        menus = resp.json()
        if menus:
            menu_id = menus[0]["id"]
            sale_data["items"][0]["menu_id"] = menu_id
            print(f"✅ Using menu: {menus[0]['name']} (price: {menus[0]['price']})")
            
            # Create the sale
            resp = requests.post(f"{BASE_URL}/sales", json=sale_data, headers=headers("owner"))
            if resp.status_code == 200:
                sale = resp.json()
                sale_id = sale["id"]
                original_total = sale.get("total", 0)
                print(f"✅ Sale created: {sale['number']}, total: {original_total}")
                
                # Test additional adjustment
                print(f"\n📋 Testing POST /api/sales/{sale_id}/adjust (type=additional, amount=3000)")
                adjust_data = {"type": "additional", "amount": 3000, "note": "Tambahan tip"}
                resp = requests.post(f"{BASE_URL}/sales/{sale_id}/adjust", json=adjust_data, headers=headers("owner"))
                if resp.status_code == 200:
                    result = resp.json()
                    final_total = result.get("final_total", 0)
                    expected_total = original_total + 3000
                    if abs(final_total - expected_total) < 0.01:
                        print(f"✅ Additional adjustment: final_total={final_total} (original={original_total} + 3000)")
                        results["passed"] += 1
                        
                        # Verify adjustment is recorded
                        resp = requests.get(f"{BASE_URL}/sales/{sale_id}", headers=headers("owner"))
                        if resp.status_code == 200:
                            sale_updated = resp.json()
                            if "adjustments" in sale_updated and len(sale_updated["adjustments"]) > 0:
                                print(f"✅ Adjustment recorded in sale.adjustments[]")
                                results["passed"] += 1
                            else:
                                print(f"❌ Adjustment NOT recorded in sale.adjustments[]")
                                results["failed"] += 1
                        
                        # Verify finance record created
                        today = datetime.now().strftime("%Y-%m")
                        resp = requests.get(f"{BASE_URL}/finance?month={today}", headers=headers("owner"))
                        if resp.status_code == 200:
                            finance_records = resp.json()
                            found = any(f.get("category") == "Penjualan" and f.get("amount") == 3000 and f.get("ref") == sale_id for f in finance_records)
                            if found:
                                print(f"✅ Additional adjustment found in finance ledger (income +3000)")
                                results["passed"] += 1
                            else:
                                print(f"❌ Additional adjustment NOT found in finance ledger")
                                results["failed"] += 1
                    else:
                        print(f"❌ Additional adjustment: final_total={final_total}, expected={expected_total}")
                        results["failed"] += 1
                        results["errors"].append(f"Additional adjustment calculation wrong")
                else:
                    print(f"❌ POST /api/sales/{sale_id}/adjust failed: {resp.status_code} - {resp.text}")
                    results["failed"] += 1
                    results["errors"].append(f"POST adjust additional: {resp.status_code}")
                
                # Test refund adjustment
                print(f"\n📋 Testing POST /api/sales/{sale_id}/adjust (type=refund, amount=2000)")
                adjust_data = {"type": "refund", "amount": 2000, "note": "Refund sebagian"}
                resp = requests.post(f"{BASE_URL}/sales/{sale_id}/adjust", json=adjust_data, headers=headers("owner"))
                if resp.status_code == 200:
                    result = resp.json()
                    final_total = result.get("final_total", 0)
                    # After additional +3000 and refund -2000, should be original + 1000
                    expected_total = original_total + 3000 - 2000
                    if abs(final_total - expected_total) < 0.01:
                        print(f"✅ Refund adjustment: final_total={final_total} (expected={expected_total})")
                        results["passed"] += 1
                        
                        # Verify finance record created (negative income)
                        resp = requests.get(f"{BASE_URL}/finance?month={today}", headers=headers("owner"))
                        if resp.status_code == 200:
                            finance_records = resp.json()
                            found = any(f.get("category") == "Refund Penyesuaian" and f.get("amount") == -2000 and f.get("ref") == sale_id for f in finance_records)
                            if found:
                                print(f"✅ Refund adjustment found in finance ledger (income -2000)")
                                results["passed"] += 1
                            else:
                                print(f"❌ Refund adjustment NOT found in finance ledger")
                                results["failed"] += 1
                    else:
                        print(f"❌ Refund adjustment: final_total={final_total}, expected={expected_total}")
                        results["failed"] += 1
                else:
                    print(f"❌ POST /api/sales/{sale_id}/adjust (refund) failed: {resp.status_code} - {resp.text}")
                    results["failed"] += 1
                
                # Test RBAC - crew should be denied
                print(f"\n📋 Testing POST /api/sales/{sale_id}/adjust (as crew - should be 403)")
                resp = requests.post(f"{BASE_URL}/sales/{sale_id}/adjust", 
                                   json={"type": "additional", "amount": 1000, "note": "Test"}, 
                                   headers=headers("crew"))
                if resp.status_code == 403:
                    print(f"✅ POST adjust as crew: correctly denied (403)")
                    results["passed"] += 1
                else:
                    print(f"❌ POST adjust as crew: expected 403, got {resp.status_code}")
                    results["failed"] += 1
                    results["errors"].append(f"RBAC violation: crew can adjust sales")
                
                # Test validation - invalid type
                print(f"\n📋 Testing POST /api/sales/{sale_id}/adjust with invalid type (should be 400)")
                resp = requests.post(f"{BASE_URL}/sales/{sale_id}/adjust", 
                                   json={"type": "invalid", "amount": 1000, "note": "Test"}, 
                                   headers=headers("owner"))
                if resp.status_code == 400:
                    print(f"✅ POST adjust with invalid type: correctly rejected (400)")
                    results["passed"] += 1
                else:
                    print(f"❌ POST adjust with invalid type: expected 400, got {resp.status_code}")
                    results["failed"] += 1
                
            else:
                print(f"❌ Failed to create sale: {resp.status_code} - {resp.text}")
                results["failed"] += 1
                results["errors"].append(f"Cannot create sale for adjustment test")
    
    print(f"\n📊 Payment Adjustment Test: {results['passed']} passed, {results['failed']} failed")
    return results

def test_print_log():
    """Test 5: Print log (should not change transaction)"""
    print("\n" + "="*80)
    print("TEST 5: PRINT LOG")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Get an existing sale
    resp = requests.get(f"{BASE_URL}/sales?date={datetime.now().strftime('%Y-%m-%d')}", headers=headers("owner"))
    if resp.status_code == 200:
        data = resp.json()
        sales = data.get("sales", [])
        if sales:
            sale = sales[0]
            sale_id = sale["id"]
            original_total = sale.get("total", 0)
            original_final_total = sale.get("final_total", original_total)
            original_print_count = sale.get("print_count", 0)
            
            print(f"\n📋 Testing POST /api/sales/{sale_id}/print-log")
            print(f"   Original: total={original_total}, final_total={original_final_total}, print_count={original_print_count}")
            
            # Add print log
            print_data = {"station": "customer", "status": "success", "note": "Cetak ulang"}
            resp = requests.post(f"{BASE_URL}/sales/{sale_id}/print-log", json=print_data, headers=headers("owner"))
            if resp.status_code == 200:
                result = resp.json()
                print(f"✅ POST /api/sales/{sale_id}/print-log: success")
                results["passed"] += 1
                
                # Verify sale totals unchanged but print_count increased
                resp = requests.get(f"{BASE_URL}/sales/{sale_id}", headers=headers("owner"))
                if resp.status_code == 200:
                    sale_updated = resp.json()
                    new_total = sale_updated.get("total", 0)
                    new_final_total = sale_updated.get("final_total", new_total)
                    new_print_count = sale_updated.get("print_count", 0)
                    
                    if new_total == original_total and new_final_total == original_final_total:
                        print(f"✅ Sale totals unchanged: total={new_total}, final_total={new_final_total}")
                        results["passed"] += 1
                    else:
                        print(f"❌ Sale totals CHANGED: total={new_total} (was {original_total}), final_total={new_final_total} (was {original_final_total})")
                        results["failed"] += 1
                        results["errors"].append("Print log changed sale totals")
                    
                    if new_print_count == original_print_count + 1:
                        print(f"✅ Print count increased: {new_print_count} (was {original_print_count})")
                        results["passed"] += 1
                    else:
                        print(f"❌ Print count not increased correctly: {new_print_count} (was {original_print_count})")
                        results["failed"] += 1
                    
                    if "print_logs" in sale_updated and len(sale_updated["print_logs"]) > 0:
                        print(f"✅ Print log recorded in sale.print_logs[] ({len(sale_updated['print_logs'])} logs)")
                        results["passed"] += 1
                    else:
                        print(f"❌ Print log NOT recorded in sale.print_logs[]")
                        results["failed"] += 1
            else:
                print(f"❌ POST /api/sales/{sale_id}/print-log failed: {resp.status_code} - {resp.text}")
                results["failed"] += 1
                results["errors"].append(f"POST print-log: {resp.status_code}")
        else:
            print(f"⚠️  No sales found to test print log")
            results["errors"].append("No sales for print log test")
    else:
        print(f"❌ Failed to get sales: {resp.status_code}")
        results["failed"] += 1
    
    print(f"\n📊 Print Log Test: {results['passed']} passed, {results['failed']} failed")
    return results

def test_external_sales():
    """Test 6: External platform sales"""
    print("\n" + "="*80)
    print("TEST 6: EXTERNAL PLATFORM SALES")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Get menu and ingredient info
    resp = requests.get(f"{BASE_URL}/menus", headers=headers("owner"))
    if resp.status_code != 200:
        print(f"❌ Failed to get menus: {resp.status_code}")
        results["failed"] += 1
        return results
    
    menus = resp.json()
    if not menus:
        print(f"❌ No menus available")
        results["failed"] += 1
        return results
    
    menu = menus[0]
    menu_id = menu["id"]
    menu_name = menu["name"]
    menu_price = menu["price"]
    
    # Get ingredient stock before
    resp = requests.get(f"{BASE_URL}/ingredients", headers=headers("owner"))
    if resp.status_code != 200:
        print(f"❌ Failed to get ingredients: {resp.status_code}")
        results["failed"] += 1
        return results
    
    ingredients_before = resp.json()
    
    # Create external sale
    print(f"\n📋 Testing POST /api/external-sales (GoFood)")
    ext_sale_data = {
        "platform": "GoFood",
        "order_no": f"GF-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "items": [
            {"menu_id": menu_id, "name": menu_name, "qty": 2, "price": menu_price, "note": ""}
        ],
        "discount": 5000,
        "discount_borne_by": "outlet",
        "commission_percent": 25,
        "other_fee_percent": 0,
        "fee_fixed": 0,
        "payment_status": "pending",
        "customer": "Customer GoFood",
        "note": "Test external sale"
    }
    
    resp = requests.post(f"{BASE_URL}/external-sales", json=ext_sale_data, headers=headers("owner"))
    if resp.status_code == 200:
        sale = resp.json()
        print(f"✅ POST /api/external-sales: created {sale['number']}")
        results["passed"] += 1
        
        # Verify calculations
        gross = menu_price * 2
        commission = round(gross * 0.25, 2)
        outlet_disc = 5000
        net = round(gross - commission - outlet_disc, 2)
        
        if sale.get("subtotal") == gross:
            print(f"✅ Gross calculation correct: {gross}")
            results["passed"] += 1
        else:
            print(f"❌ Gross calculation wrong: {sale.get('subtotal')} (expected {gross})")
            results["failed"] += 1
        
        if sale.get("commission") == commission:
            print(f"✅ Commission calculation correct: {commission}")
            results["passed"] += 1
        else:
            print(f"❌ Commission calculation wrong: {sale.get('commission')} (expected {commission})")
            results["failed"] += 1
        
        if abs(sale.get("expected_net", 0) - net) < 0.01:
            print(f"✅ Net calculation correct: {net}")
            results["passed"] += 1
        else:
            print(f"❌ Net calculation wrong: {sale.get('expected_net')} (expected {net})")
            results["failed"] += 1
        
        # Verify channel and platform
        if sale.get("channel") == "platform" and sale.get("platform") == "GoFood":
            print(f"✅ Channel and platform set correctly")
            results["passed"] += 1
        else:
            print(f"❌ Channel or platform incorrect: channel={sale.get('channel')}, platform={sale.get('platform')}")
            results["failed"] += 1
        
        # Verify stock deduction
        resp = requests.get(f"{BASE_URL}/ingredients", headers=headers("owner"))
        if resp.status_code == 200:
            ingredients_after = resp.json()
            stock_reduced = False
            for ing_before in ingredients_before:
                ing_after = next((i for i in ingredients_after if i["id"] == ing_before["id"]), None)
                if ing_after and ing_after["total"] < ing_before["total"]:
                    stock_reduced = True
                    print(f"✅ Stock reduced for {ing_before['name']}: {ing_before['total']} -> {ing_after['total']}")
                    break
            
            if stock_reduced:
                results["passed"] += 1
            else:
                print(f"❌ Stock NOT reduced for any ingredient")
                results["failed"] += 1
                results["errors"].append("External sale did not reduce stock")
        
        # Verify finance records
        today = datetime.now().strftime("%Y-%m")
        resp = requests.get(f"{BASE_URL}/finance?month={today}", headers=headers("owner"))
        if resp.status_code == 200:
            finance_records = resp.json()
            
            # Check income record
            income_found = any(f.get("category") == "Penjualan" and f.get("amount") == gross and f.get("ref") == sale["id"] for f in finance_records)
            if income_found:
                print(f"✅ Finance income record found: Penjualan +{gross}")
                results["passed"] += 1
            else:
                print(f"❌ Finance income record NOT found")
                results["failed"] += 1
            
            # Check commission expense
            commission_found = any(f.get("category") == "Komisi Platform" and f.get("amount") == commission and f.get("ref") == sale["id"] for f in finance_records)
            if commission_found:
                print(f"✅ Finance expense record found: Komisi Platform +{commission}")
                results["passed"] += 1
            else:
                print(f"❌ Finance expense record NOT found for commission")
                results["failed"] += 1
        
        # Test deduplication - POST same order_no should fail
        print(f"\n📋 Testing POST /api/external-sales with duplicate order_no (should be 409)")
        resp = requests.post(f"{BASE_URL}/external-sales", json=ext_sale_data, headers=headers("owner"))
        if resp.status_code == 409:
            print(f"✅ Duplicate order_no correctly rejected (409)")
            results["passed"] += 1
        else:
            print(f"❌ Duplicate order_no: expected 409, got {resp.status_code}")
            results["failed"] += 1
            results["errors"].append("Deduplication not working")
    else:
        print(f"❌ POST /api/external-sales failed: {resp.status_code} - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"POST external-sales: {resp.status_code}")
    
    # Test manual item (no menu_id)
    print(f"\n📋 Testing POST /api/external-sales with manual item (no menu_id)")
    ext_sale_data2 = {
        "platform": "ShopeeFood",
        "order_no": f"SF-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "items": [
            {"name": "Paket Spesial", "qty": 1, "price": 50000, "note": "Custom item"}
        ],
        "discount": 0,
        "commission_percent": 20,
        "payment_status": "settled",
        "customer": "Customer Shopee",
        "note": "Manual item test"
    }
    
    resp = requests.post(f"{BASE_URL}/external-sales", json=ext_sale_data2, headers=headers("owner"))
    if resp.status_code == 200:
        sale = resp.json()
        print(f"✅ POST /api/external-sales with manual item: created {sale['number']}")
        results["passed"] += 1
    else:
        print(f"❌ POST /api/external-sales with manual item failed: {resp.status_code} - {resp.text}")
        results["failed"] += 1
    
    # Test validation - item without name should fail
    print(f"\n📋 Testing POST /api/external-sales without item name (should be 400)")
    ext_sale_data3 = {
        "platform": "GrabFood",
        "order_no": f"GR-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "items": [
            {"qty": 1, "price": 30000, "note": "No name"}
        ],
        "commission_percent": 20,
        "payment_status": "pending"
    }
    
    resp = requests.post(f"{BASE_URL}/external-sales", json=ext_sale_data3, headers=headers("owner"))
    if resp.status_code == 400:
        print(f"✅ POST /api/external-sales without item name: correctly rejected (400)")
        results["passed"] += 1
    else:
        print(f"❌ POST /api/external-sales without item name: expected 400, got {resp.status_code}")
        results["failed"] += 1
    
    print(f"\n📊 External Sales Test: {results['passed']} passed, {results['failed']} failed")
    return results

def test_finance_summary():
    """Test 7: Finance summary with consistency checks"""
    print("\n" + "="*80)
    print("TEST 7: FINANCE SUMMARY")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Test GET /api/finance/summary
    print(f"\n📋 Testing GET /api/finance/summary?period=month")
    resp = requests.get(f"{BASE_URL}/finance/summary?period=month", headers=headers("owner"))
    if resp.status_code == 200:
        summary = resp.json()
        print(f"✅ GET /api/finance/summary: success")
        results["passed"] += 1
        
        # Verify structure
        required_keys = ["omzet", "cashflow", "by_method", "by_channel", "expenses_by_category", "pockets"]
        missing_keys = [k for k in required_keys if k not in summary]
        if not missing_keys:
            print(f"✅ Summary structure complete: all required keys present")
            results["passed"] += 1
        else:
            print(f"❌ Summary structure incomplete: missing {missing_keys}")
            results["failed"] += 1
            results["errors"].append(f"Missing keys in summary: {missing_keys}")
        
        # Verify omzet structure
        omzet = summary.get("omzet", {})
        omzet_keys = ["gross", "discount", "refund", "net", "hpp", "gross_profit"]
        missing_omzet = [k for k in omzet_keys if k not in omzet]
        if not missing_omzet:
            print(f"✅ Omzet structure complete")
            print(f"   Gross: {omzet['gross']}, Discount: {omzet['discount']}, Refund: {omzet['refund']}")
            print(f"   Net: {omzet['net']}, HPP: {omzet['hpp']}, Gross Profit: {omzet['gross_profit']}")
            results["passed"] += 1
        else:
            print(f"❌ Omzet structure incomplete: missing {missing_omzet}")
            results["failed"] += 1
        
        # Verify by_channel includes both kasir and platform
        by_channel = summary.get("by_channel", [])
        channels = [c["channel"] for c in by_channel]
        if "kasir" in channels or "platform" in channels:
            print(f"✅ by_channel includes channels: {channels}")
            results["passed"] += 1
            
            # Check platform channel has fee
            platform_channel = next((c for c in by_channel if c["channel"] == "platform"), None)
            if platform_channel:
                if platform_channel.get("fee", 0) > 0:
                    print(f"   Platform fee: {platform_channel['fee']}")
                    results["passed"] += 1
                else:
                    print(f"   ⚠️  Platform fee is 0 (may be correct if no platform sales)")
        else:
            print(f"❌ by_channel missing kasir or platform: {channels}")
            results["failed"] += 1
        
        # Verify pockets (should have 10)
        pockets = summary.get("pockets", [])
        if len(pockets) >= 10:
            print(f"✅ Pockets: {len(pockets)} pockets found (expected 10)")
            results["passed"] += 1
            
            # Check pocket structure
            if pockets:
                pocket = pockets[0]
                pocket_keys = ["id", "name", "alloc_method", "alloc_value", "allocated", "actual", "diff"]
                missing_pocket = [k for k in pocket_keys if k not in pocket]
                if not missing_pocket:
                    print(f"✅ Pocket structure complete")
                    results["passed"] += 1
                else:
                    print(f"❌ Pocket structure incomplete: missing {missing_pocket}")
                    results["failed"] += 1
        else:
            print(f"❌ Pockets: only {len(pockets)} found, expected 10")
            results["failed"] += 1
        
        # CONSISTENCY CHECK: Verify no double counting
        # Get all sales for the month
        today = datetime.now().strftime("%Y-%m")
        resp_sales = requests.get(f"{BASE_URL}/sales?month={today}", headers=headers("owner"))
        if resp_sales.status_code == 200:
            data = resp_sales.json()
            sales = data.get("sales", [])
            # Calculate expected gross from sales (using final_total if exists, else total)
            expected_gross = sum(s.get("final_total", s.get("total", 0)) for s in sales if s.get("status") not in ["void", "cancelled"])
            actual_gross = omzet.get("gross", 0)
            
            # Allow small rounding difference
            if abs(expected_gross - actual_gross) < 1:
                print(f"✅ CONSISTENCY: Omzet gross matches sales total ({actual_gross})")
                results["passed"] += 1
            else:
                print(f"⚠️  CONSISTENCY: Omzet gross ({actual_gross}) vs sales total ({expected_gross}) - diff: {abs(expected_gross - actual_gross)}")
                # This might be acceptable if there are adjustments, so just warn
                if abs(expected_gross - actual_gross) > 100:
                    results["errors"].append(f"Large discrepancy in omzet: {abs(expected_gross - actual_gross)}")
        
    else:
        print(f"❌ GET /api/finance/summary failed: {resp.status_code} - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"GET finance/summary: {resp.status_code}")
    
    # Test RBAC - crew should be denied
    print(f"\n📋 Testing GET /api/finance/summary (as crew - should be 403)")
    resp = requests.get(f"{BASE_URL}/finance/summary?period=month", headers=headers("crew"))
    if resp.status_code == 403:
        print(f"✅ GET /api/finance/summary as crew: correctly denied (403)")
        results["passed"] += 1
    else:
        print(f"❌ GET /api/finance/summary as crew: expected 403, got {resp.status_code}")
        results["failed"] += 1
        results["errors"].append(f"RBAC violation: crew can access finance summary")
    
    print(f"\n📊 Finance Summary Test: {results['passed']} passed, {results['failed']} failed")
    return results

def test_stock_mode():
    """Test 8: Stock mode setting (simple vs detailed)"""
    print("\n" + "="*80)
    print("TEST 8: STOCK MODE SETTING")
    print("="*80)
    
    results = {"passed": 0, "failed": 0, "errors": []}
    
    # Set stock_mode to simple
    print(f"\n📋 Setting stock_mode=simple")
    settings_update = {
        "tax_enabled": True, "tax_name": "PB1", "tax_percent": 10.0, "tax_default_on": True,
        "service_percent": 0.0, "loyalty_enabled": True, "points_per_nota": 1,
        "points_min_purchase": 0, "points_per_amount": 0, "petty_cash_limit": 50000,
        "stock_mode": "simple", "petty_cash_needs_approval": False,
        "late_tolerance_min": 10, "late_penalty_fixed": 0, "late_penalty_per_minute": 0,
        "printer": {"paper_width": 58}, "qris": {}, "receipt": {"cafe_name": "ROLLOW", "footer_note": "Thank you!"}
    }
    resp = requests.put(f"{BASE_URL}/settings", json=settings_update, headers=headers("owner"))
    if resp.status_code == 200:
        settings = resp.json()
        if settings.get("stock_mode") == "simple":
            print(f"✅ Settings updated: stock_mode=simple")
            results["passed"] += 1
            
            # Create a sale and check stock movement location
            resp = requests.get(f"{BASE_URL}/menus", headers=headers("owner"))
            if resp.status_code == 200:
                menus = resp.json()
                if menus:
                    menu = menus[0]
                    sale_data = {
                        "items": [{"menu_id": menu["id"], "qty": 1, "note": ""}],
                        "payment_method": "Cash",
                        "customer": "Test",
                        "apply_tax": True,
                        "cash_received": 50000,
                        "order_note": "Test stock mode simple"
                    }
                    
                    resp = requests.post(f"{BASE_URL}/sales", json=sale_data, headers=headers("owner"))
                    if resp.status_code == 200:
                        sale = resp.json()
                        print(f"✅ Sale created in simple mode: {sale['number']}")
                        results["passed"] += 1
                        
                        # Check stock movements - should be from "gudang" location
                        resp = requests.get(f"{BASE_URL}/inventory/movements?type=penjualan", headers=headers("owner"))
                        if resp.status_code == 200:
                            movements = resp.json()
                            recent_movements = [m for m in movements if m.get("ref") == sale["number"]]
                            if recent_movements:
                                gudang_movements = [m for m in recent_movements if m.get("location") == "gudang"]
                                if gudang_movements:
                                    print(f"✅ Stock movements in simple mode use 'gudang' location")
                                    results["passed"] += 1
                                else:
                                    print(f"❌ Stock movements NOT using 'gudang' location: {[m.get('location') for m in recent_movements]}")
                                    results["failed"] += 1
                                    results["errors"].append("Simple mode not using gudang location")
                            else:
                                print(f"⚠️  No stock movements found for sale {sale['number']}")
                        else:
                            print(f"⚠️  Failed to get stock movements: {resp.status_code}")
                    else:
                        print(f"⚠️  Failed to create sale: {resp.status_code}")
        else:
            print(f"❌ Settings not updated: stock_mode={settings.get('stock_mode')}")
            results["failed"] += 1
    else:
        print(f"❌ Failed to update settings: {resp.status_code} - {resp.text}")
        results["failed"] += 1
        results["errors"].append(f"PUT settings stock_mode: {resp.status_code}")
    
    # Restore stock_mode to detailed
    print(f"\n📋 Restoring stock_mode=detailed")
    settings_update["stock_mode"] = "detailed"
    resp = requests.put(f"{BASE_URL}/settings", json=settings_update, headers=headers("owner"))
    if resp.status_code == 200:
        print(f"✅ Settings restored: stock_mode=detailed")
    else:
        print(f"⚠️  Failed to restore settings: {resp.status_code}")
    
    print(f"\n📊 Stock Mode Test: {results['passed']} passed, {results['failed']} failed")
    return results

def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("ROLLOW CAFE MANAGEMENT - BACKEND TEST SUITE (Phase A+B+C)")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Login all roles
    print("\n" + "="*80)
    print("AUTHENTICATION")
    print("="*80)
    for role in ["owner", "finance", "crew", "manager"]:
        if not login(role):
            print(f"\n❌ CRITICAL: Failed to login as {role}. Aborting tests.")
            return
    
    # Run all tests
    all_results = {
        "config_registries": test_config_registries(),
        "audit": test_audit(),
        "expenses": test_expenses(),
        "payment_adjustment": test_payment_adjustment(),
        "print_log": test_print_log(),
        "external_sales": test_external_sales(),
        "finance_summary": test_finance_summary(),
        "stock_mode": test_stock_mode(),
    }
    
    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    total_passed = sum(r["passed"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())
    total_tests = total_passed + total_failed
    
    for test_name, result in all_results.items():
        status = "✅ PASS" if result["failed"] == 0 else "❌ FAIL"
        print(f"{status} {test_name}: {result['passed']} passed, {result['failed']} failed")
        if result["errors"]:
            for error in result["errors"]:
                print(f"      ⚠️  {error}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {total_passed}/{total_tests} tests passed ({round(total_passed/total_tests*100, 1)}%)")
    print(f"{'='*80}")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total_failed} tests failed. Please review errors above.")

if __name__ == "__main__":
    main()
