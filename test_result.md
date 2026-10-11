#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

## user_problem_statement: Import project dari GitHub repository https://github.com/trecianayuli04-ctrl/rlwmanageapp.git (branch main), setup dan install semua dependencies. App = ROLLOW Cafe Management (POS, inventory, payroll, attendance, finance, marketing, reports) — Expo frontend + FastAPI backend + MongoDB.

## backend:
##   - task: "Import repo & fix broken ext_routes import"
##     implemented: true
##     working: true
##     file: "backend/server.py"
##     stuck_count: 0
##     priority: "high"
##     needs_retesting: false
##     status_history:
##         -working: true
##         -agent: "main"
##         -comment: "Local /app already in sync with origin/main (commit 44e0fc7). server.py imported missing module ext_routes (never committed to repo, not needed by frontend/tests). Removed lines 1362-1365 (import + include_router + startup handler). Backend starts OK, POST /api/auth/login with owner@rollow.id/Rollow@2026 returns JWT."
##         -working: true
##         -agent: "testing"
##         -comment: "SMOKE TEST PASSED (8/8). Verified ext_routes removal successful. All endpoints working: (1) POST /api/auth/login owner → 200 OK with access_token + user data, (2) GET /api/auth/me → 200 OK owner data, (3) GET /api/dashboard → 200 OK with sales/trx/profit/low_stock/finance data, (4) GET /api/menus → 200 OK returned 6 menu items (Roti Bakar Telur, Americano, Coklat Panas, etc), (5) GET /api/settings → 200 OK with tax/service/loyalty/printer/qris config, (6) GET /api/register/current → 200 OK (no active session), (7) POST /api/auth/login crew → 200 OK, (8) GET /api/attendance/live → 200 OK with RBAC working. Backend logs clean (no ModuleNotFoundError, no 500 errors). Server stable (uptime 0:02:40, supervisor status RUNNING). Test credentials from /app/memory/test_credentials.md verified working."
##   - task: "Install backend dependencies"
##     implemented: true
##     working: true
##     file: "backend/requirements.txt"
##     stuck_count: 0
##     priority: "high"
##     needs_retesting: false
##     status_history:
##         -working: true
##         -agent: "main"
##         -comment: "pip install -r requirements.txt — all satisfied incl. emergentintegrations==0.2.2"

## frontend:
##   - task: "Install frontend dependencies"
##     implemented: true
##     working: true
##     file: "frontend/package.json"
##     stuck_count: 0
##     priority: "high"
##     needs_retesting: false
##     status_history:
##         -working: true
##         -agent: "main"
##         -comment: "yarn install --frozen-lockfile completed OK (only harmless peer-dep warnings). Expo service restarted, login screen renders correctly at preview URL."

## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 2
##   run_ui: false

## test_plan:
##   current_focus: []
##   stuck_tasks: []
##   test_all: false
##   test_priority: "high_first"

## agent_communication:
##     -agent: "main"
##     -message: "Setup/import selesai. Tolong smoke-test backend: (1) POST /api/auth/login owner@rollow.id / Rollow@2026 -> token, (2) GET /api/auth/me dengan token, (3) GET /api/dashboard, (4) GET /api/menus, (5) GET /api/settings. Kredensial ada di /app/memory/test_credentials.md. Fokus verifikasi server stabil setelah penghapusan import ext_routes."
##     -agent: "testing"
##     -message: "Backend smoke test COMPLETE - ALL PASSED (8/8 tests). Server stabil setelah penghapusan ext_routes. Semua endpoint core berfungsi dengan baik: auth (owner & crew login), dashboard, menus (6 items), settings, register status, attendance live. RBAC working correctly. No errors di backend logs. Backend service RUNNING stable. Ready for production use or further feature development."