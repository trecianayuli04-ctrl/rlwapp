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
## Backlog
- P1: Multi-outlet switcher UI, printable/shareable receipts (Bluetooth printer), shift scheduling, assign opname tasks to crew
- P2: Charts on reports, export Excel/PDF, supplier management, split server.py into routers
