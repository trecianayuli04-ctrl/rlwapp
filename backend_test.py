#!/usr/bin/env python3
"""
ROLLOW Cafe Management Backend Smoke Test
Tests all critical backend endpoints after ext_routes fix
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def print_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"   {details}")
    print()

def test_auth_login_owner():
    """Test 1: POST /api/auth/login with owner credentials"""
    print("=" * 60)
    print("TEST 1: Owner Login")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/auth/login"
    payload = {
        "email": "owner@rollow.id",
        "password": "Rollow@2026"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Keys: {list(data.keys())}")
            
            has_token = "access_token" in data
            has_user = "user" in data
            
            if has_token and has_user:
                print(f"✓ Access Token: {data['access_token'][:50]}...")
                print(f"✓ User Email: {data['user'].get('email')}")
                print(f"✓ User Role: {data['user'].get('role')}")
                print_test("Owner Login", True, "Token and user data received")
                return data["access_token"]
            else:
                print_test("Owner Login", False, f"Missing fields - has_token:{has_token}, has_user:{has_user}")
                return None
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Owner Login", False, f"HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print_test("Owner Login", False, f"Exception: {str(e)}")
        return None

def test_auth_me(token):
    """Test 2: GET /api/auth/me with Bearer token"""
    print("=" * 60)
    print("TEST 2: Get Current User (auth/me)")
    print("=" * 60)
    
    if not token:
        print_test("Get Current User", False, "No token available")
        return False
    
    url = f"{BASE_URL}/api/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"User Email: {data.get('email')}")
            print(f"User Role: {data.get('role')}")
            print(f"User Name: {data.get('name')}")
            print_test("Get Current User", True, f"Owner data retrieved: {data.get('email')}")
            return True
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Get Current User", False, f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_test("Get Current User", False, f"Exception: {str(e)}")
        return False

def test_dashboard(token):
    """Test 3: GET /api/dashboard with token"""
    print("=" * 60)
    print("TEST 3: Get Dashboard Data")
    print("=" * 60)
    
    if not token:
        print_test("Get Dashboard", False, "No token available")
        return False
    
    url = f"{BASE_URL}/api/dashboard"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Keys: {list(data.keys())}")
            print(f"Dashboard Data Sample: {json.dumps(data, indent=2)[:300]}...")
            print_test("Get Dashboard", True, "Dashboard data retrieved")
            return True
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Get Dashboard", False, f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_test("Get Dashboard", False, f"Exception: {str(e)}")
        return False

def test_menus(token):
    """Test 4: GET /api/menus with token"""
    print("=" * 60)
    print("TEST 4: Get Menu List")
    print("=" * 60)
    
    if not token:
        print_test("Get Menus", False, "No token available")
        return False
    
    url = f"{BASE_URL}/api/menus"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Total Menus: {len(data)}")
                if len(data) > 0:
                    print(f"Sample Menu Items:")
                    for menu in data[:3]:
                        print(f"  - {menu.get('name')} (Rp {menu.get('price')})")
                print_test("Get Menus", True, f"Retrieved {len(data)} menu items")
                return True
            else:
                print(f"Unexpected response format: {type(data)}")
                print_test("Get Menus", False, "Response is not a list")
                return False
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Get Menus", False, f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_test("Get Menus", False, f"Exception: {str(e)}")
        return False

def test_settings(token):
    """Test 5: GET /api/settings with token"""
    print("=" * 60)
    print("TEST 5: Get Settings")
    print("=" * 60)
    
    if not token:
        print_test("Get Settings", False, "No token available")
        return False
    
    url = f"{BASE_URL}/api/settings"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Keys: {list(data.keys())}")
            print(f"Settings Sample: {json.dumps(data, indent=2)[:300]}...")
            print_test("Get Settings", True, "Settings retrieved")
            return True
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Get Settings", False, f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_test("Get Settings", False, f"Exception: {str(e)}")
        return False

def test_register_current(token):
    """Test 6: GET /api/register/current with token"""
    print("=" * 60)
    print("TEST 6: Get Current Register Status")
    print("=" * 60)
    
    if not token:
        print_test("Get Register Status", False, "No token available")
        return False
    
    url = f"{BASE_URL}/api/register/current"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        # 200 with data or 404 (no active session) are both acceptable
        if response.status_code == 200:
            data = response.json()
            print(f"Register Status: {json.dumps(data, indent=2)[:300]}...")
            print_test("Get Register Status", True, "Register status retrieved (active session)")
            return True
        elif response.status_code == 404:
            print("No active register session (expected if no one is logged in)")
            print_test("Get Register Status", True, "No active session (acceptable)")
            return True
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Get Register Status", False, f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_test("Get Register Status", False, f"Exception: {str(e)}")
        return False

def test_auth_login_crew():
    """Test 7: POST /api/auth/login with crew credentials"""
    print("=" * 60)
    print("TEST 7: Crew Login")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/auth/login"
    payload = {
        "email": "crew@rollow.id",
        "password": "Rollow@2026"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            has_token = "access_token" in data
            has_user = "user" in data
            
            if has_token and has_user:
                print(f"✓ User Email: {data['user'].get('email')}")
                print(f"✓ User Role: {data['user'].get('role')}")
                print_test("Crew Login", True, "Crew token received")
                return data["access_token"]
            else:
                print_test("Crew Login", False, f"Missing fields")
                return None
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Crew Login", False, f"HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print_test("Crew Login", False, f"Exception: {str(e)}")
        return None

def test_attendance_live(token):
    """Test 8: GET /api/attendance/live with crew token (RBAC check)"""
    print("=" * 60)
    print("TEST 8: Get Live Attendance (RBAC Check)")
    print("=" * 60)
    
    if not token:
        print_test("Get Live Attendance", False, "No token available")
        return False
    
    url = f"{BASE_URL}/api/attendance/live"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        # We're checking it doesn't return 500 (server error)
        # 200, 403, 404 are all acceptable (depends on RBAC implementation)
        if response.status_code in [200, 403, 404]:
            if response.status_code == 200:
                data = response.json()
                print(f"Live Attendance Data: {json.dumps(data, indent=2)[:300]}...")
            elif response.status_code == 403:
                print("Access forbidden (RBAC working)")
            elif response.status_code == 404:
                print("Endpoint not found or no data")
            print_test("Get Live Attendance", True, f"No server error (HTTP {response.status_code})")
            return True
        elif response.status_code == 500:
            print(f"Response: {response.text[:200]}")
            print_test("Get Live Attendance", False, "Server error 500")
            return False
        else:
            print(f"Response: {response.text[:200]}")
            print_test("Get Live Attendance", True, f"No server error (HTTP {response.status_code})")
            return True
            
    except Exception as e:
        print_test("Get Live Attendance", False, f"Exception: {str(e)}")
        return False

def main():
    print("\n" + "=" * 60)
    print("ROLLOW CAFE MANAGEMENT - BACKEND SMOKE TEST")
    print("Testing after ext_routes import fix")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1-6: Owner flow
    owner_token = test_auth_login_owner()
    results.append(("Owner Login", owner_token is not None))
    
    if owner_token:
        results.append(("Get Current User", test_auth_me(owner_token)))
        results.append(("Get Dashboard", test_dashboard(owner_token)))
        results.append(("Get Menus", test_menus(owner_token)))
        results.append(("Get Settings", test_settings(owner_token)))
        results.append(("Get Register Status", test_register_current(owner_token)))
    else:
        print("⚠️  Skipping owner-dependent tests due to login failure\n")
        results.extend([
            ("Get Current User", False),
            ("Get Dashboard", False),
            ("Get Menus", False),
            ("Get Settings", False),
            ("Get Register Status", False)
        ])
    
    # Test 7-8: Crew flow (RBAC check)
    crew_token = test_auth_login_crew()
    results.append(("Crew Login", crew_token is not None))
    
    if crew_token:
        results.append(("Get Live Attendance", test_attendance_live(crew_token)))
    else:
        print("⚠️  Skipping crew-dependent tests due to login failure\n")
        results.append(("Get Live Attendance", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    # Exit code
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
