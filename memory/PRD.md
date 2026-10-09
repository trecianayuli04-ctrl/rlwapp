# ROLLOW Cafe Management — PRD
## Problem
Integrated cafe management app for ROLLOW (POS, recipes/HPP, inventory per location, stock opname, waste, purchasing, finance, payroll, attendance, marketing, reports) with role-based access: Owner, Manager, Supervisor, Finance, Marketing, Crew. Responsive phone/tablet/web. Multi-outlet ready.
## Architecture
- Backend: FastAPI single server.py, MongoDB (uuid `id`, `outlet_id` on every doc), JWT (bcrypt) + Emergent Google sign-in (/api/auth/session, only for emails registered by Owner, returns ROLLOW JWT).
- Frontend: Expo Router; tabs Beranda/Kasir/Stok/Lainnya (role-hidden), module screens under /m/*. Theme terracotta.
## Implemented (2026-06)
- Auth + RBAC (backend authoritative), demo accounts (see test_credentials.md)
- POS: categories, cart, promo, Cash/QRIS/Transfer/Debit, receipt, close register
- Sale -> recipe -> stock deduction (bar/kitchen) -> HPP/profit -> finance income
- Inventory in/out/transfer, min stock, low stock alerts, PR from low stock
- Stock opname with diff + value, adjusts stock; reports daily/monthly
- Waste with approval -> deduct; Purchasing request -> approve -> receive (gudang + expense)
- Finance manual tx + auto entries; Payroll from attendance -> pay -> expense
- Attendance clock in/out/izin/sakit/libur/lembur; Marketing promos/campaign + performance
- Reports: sales, inventory, opname, waste, purchasing, finance/cashflow, payroll, attendance, marketing
## Iteration 2 (2026-06)
- Riwayat Nota: recap per nota + overall recap (day/month, status filter); report type "nota"
- Void & Batalkan pesanan (SPV+ with reason): reverses stock, finance (negative income), loyalty points
- Customers & loyalty points (points per nota, min purchase, bonus per amount) — settings by Owner/Finance
- Tax (name, %, default on) + service charge; tax toggle in POS; tax recorded as separate finance income
- Tickets: customer / bar-checker / kitchen (menu.station), receipt template settings (name, address, phone, header, WiFi, footer, toggles), live preview, print via expo-print (58mm)
## Iteration 3 (2026-06)
- Shared outlet tablet: register sessions (open with opening cash; first cashier = Shift 1), PIN-based shift handover without closing, sales carry shift holder as cashier; close register shows per-shift recap & expected cash
- Kiosk attendance on POS tab (name + PIN): clock in/out, izin, sakit, libur, lembur (pending ACC by owner/manager/SPV)
- Realtime attendance (POS sheet + dashboard, 30s polling)
- Payroll auto: hourly rate x worked hours + base + allowance + approved overtime - late penalty (tolerance, fixed/per-minute in settings); realtime payroll estimate; rate editor (owner/finance)
- Tickets: Bar/Checker always printed (all items, simple), Dapur kitchen-only simple; customer receipt full
## Backlog
- P0: Direct Bluetooth ESC/POS printing (needs dev build; ticket text lines already 32-col ready)
- P1: Redeem loyalty points as discount, Multi-outlet switcher UI, printable/shareable receipts (Bluetooth printer), shift scheduling, assign opname tasks to crew
- P2: Charts on reports, export Excel/PDF, supplier management, split server.py into routers
