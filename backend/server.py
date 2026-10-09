from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import os, uuid, logging, bcrypt, jwt, httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
JWT_SECRET = os.environ['JWT_SECRET']
TZ = ZoneInfo("Asia/Jakarta")
OUTLET = "rollow-main"  # multi-outlet ready: every document carries outlet_id
LOCATIONS = ["gudang", "bar", "kitchen"]

app = FastAPI(title="ROLLOW Cafe Management")
api = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger("rollow")

# ---------------- Roles / permissions ----------------
ALL = ["owner", "manager", "supervisor", "finance", "marketing", "crew"]
OPS = ["owner", "manager", "supervisor", "crew"]
MGMT = ["owner", "manager", "supervisor"]
PERM = {
    "pos": OPS, "menu_edit": ["owner", "manager"], "inventory_view": OPS,
    "inventory_move": MGMT, "opname": OPS, "waste": OPS, "waste_approve": MGMT,
    "purchase": OPS, "purchase_approve": ["owner", "manager"], "purchase_receive": MGMT,
    "finance": ["owner", "finance"], "payroll": ["owner", "finance"],
    "attendance_all": ["owner", "manager", "supervisor", "finance"],
    "marketing": ["owner", "marketing", "manager"], "users": ["owner"], "settings": ["owner", "finance"],
    "sales_view": ["owner", "manager", "supervisor", "finance", "marketing", "crew"],
    "sales_void": ["owner", "manager", "supervisor"],
    "customers": ["owner", "manager", "supervisor", "marketing", "crew"],
}
REPORTS = {
    "sales": ["owner", "manager", "supervisor", "finance", "marketing"],
    "nota": ["owner", "manager", "supervisor", "finance"],
    "inventory": MGMT, "opname": MGMT, "waste": MGMT, "purchasing": ["owner", "manager", "supervisor", "finance"],
    "finance": ["owner", "finance"], "payroll": ["owner", "finance"],
    "attendance": ["owner", "manager", "supervisor", "finance"], "marketing": ["owner", "marketing", "manager"],
}


def now():
    return datetime.now(TZ)


def today():
    return now().strftime("%Y-%m-%d")


def nid():
    return str(uuid.uuid4())


def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_pw(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


def make_token(u):
    t = datetime.now(timezone.utc)
    return jwt.encode({"sub": u["id"], "role": u["role"], "iat": t, "exp": t + timedelta(hours=12)}, JWT_SECRET, algorithm="HS256")


def public_user(u):
    return {k: u.get(k) for k in ["id", "email", "name", "role", "position", "base_salary", "allowance", "is_active", "outlet_id"]}


async def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    if not cred:
        raise HTTPException(401, "Belum login")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token tidak valid / kedaluwarsa")
    u = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not u or not u.get("is_active", True):
        raise HTTPException(401, "User tidak aktif")
    return u


def need(perm):
    async def dep(u=Depends(current_user)):
        if u["role"] not in PERM[perm]:
            raise HTTPException(403, "Akses ditolak untuk jabatan Anda")
        return u
    return dep


async def find(col, q=None, sort="created_at", limit=1000):
    q = {**(q or {}), "outlet_id": OUTLET}
    return await db[col].find(q, {"_id": 0}).sort(sort, -1).to_list(limit)


async def insert(col, doc):
    doc = {"id": nid(), "outlet_id": OUTLET, "created_at": now().isoformat(), "date": today(), **doc}
    await db[col].insert_one(dict(doc))
    return doc


# ---------------- Inventory core ----------------
async def get_stock(ing_id, loc):
    s = await db.stocks.find_one({"ingredient_id": ing_id, "location": loc, "outlet_id": OUTLET}, {"_id": 0})
    return s["qty"] if s else 0.0


async def move_stock(ing_id, loc, delta, mtype, ref, user):
    await db.stocks.update_one({"ingredient_id": ing_id, "location": loc, "outlet_id": OUTLET},
                               {"$inc": {"qty": delta}}, upsert=True)
    ing = await db.ingredients.find_one({"id": ing_id}, {"_id": 0})
    await insert("stock_movements", {"ingredient_id": ing_id, "ingredient_name": ing["name"] if ing else "",
                                     "unit": ing["unit"] if ing else "", "location": loc, "qty": delta,
                                     "type": mtype, "ref": ref, "user_name": user.get("name", "")})


async def ingredient_map():
    return {i["id"]: i for i in await find("ingredients", sort="name")}


async def menu_hpp(menu, imap):
    return round(sum(r["qty"] * imap.get(r["ingredient_id"], {}).get("cost_per_unit", 0) for r in menu.get("recipe", [])), 2)


async def add_finance(ftype, category, amount, note, ref, user):
    return await insert("finance", {"type": ftype, "category": category, "amount": round(amount, 2),
                                    "note": note, "ref": ref, "user_name": user.get("name", "")})


# ---------------- Models ----------------
class LoginIn(BaseModel):
    email: str
    password: str


class UserIn(BaseModel):
    email: str
    password: Optional[str] = None
    name: str
    role: str
    position: str = ""
    base_salary: float = 0
    allowance: float = 0
    is_active: bool = True


class IngredientIn(BaseModel):
    name: str
    unit: str
    cost_per_unit: float
    min_stock: float = 0
    category: str = "Bahan"


class RecipeItem(BaseModel):
    ingredient_id: str
    qty: float


class MenuIn(BaseModel):
    name: str
    category: str
    price: float
    location: str = "bar"
    station: str = "bar"  # bar | kitchen -> which order ticket prints the item
    recipe: List[RecipeItem] = []
    is_active: bool = True


class SaleItem(BaseModel):
    menu_id: str
    qty: int
    note: str = ""


class SaleIn(BaseModel):
    items: List[SaleItem]
    payment_method: str
    promo_id: Optional[str] = None
    customer: str = ""
    customer_id: Optional[str] = None
    apply_tax: bool = True
    cash_received: float = 0
    order_note: str = ""


class MoveIn(BaseModel):
    ingredient_id: str
    type: str  # in | out | transfer
    qty: float
    location: str
    to_location: Optional[str] = None
    note: str = ""
    total_cost: float = 0


class OpnameLine(BaseModel):
    ingredient_id: str
    physical: float


class OpnameIn(BaseModel):
    location: str
    lines: List[OpnameLine]
    note: str = ""


class WasteIn(BaseModel):
    ingredient_id: str
    qty: float
    reason: str
    location: str


class PRItem(BaseModel):
    ingredient_id: str
    qty: float
    est_price: float = 0


class PRIn(BaseModel):
    items: List[PRItem]
    note: str = ""


class ReceiveIn(BaseModel):
    total_paid: Optional[float] = None


class DecisionIn(BaseModel):
    approve: bool
    note: str = ""


class FinanceIn(BaseModel):
    type: str  # income | expense
    category: str
    amount: float
    note: str = ""


class AttendanceIn(BaseModel):
    type: str  # clock_in | clock_out | izin | sakit | libur | lembur
    note: str = ""
    hours: float = 0


class PayrollIn(BaseModel):
    user_id: str
    month: str  # YYYY-MM
    bonus: float = 0
    deduction: float = 0
    overtime_rate: float = 25000


class PromoIn(BaseModel):
    name: str
    kind: str = "promo"  # promo | campaign
    discount_type: str = "percent"  # percent | nominal
    value: float = 0
    start_date: str
    end_date: str
    description: str = ""
    budget: float = 0
    is_active: bool = True


# ---------------- Auth & users ----------------
@api.post("/auth/login")
async def login(data: LoginIn):
    u = await db.users.find_one({"email": data.email.lower().strip()}, {"_id": 0})
    if not u or not verify_pw(data.password, u["password_hash"]) or not u.get("is_active", True):
        raise HTTPException(401, "Email atau password salah")
    return {"access_token": make_token(u), "user": public_user(u)}


class SessionIn(BaseModel):
    session_id: str


@api.post("/auth/session")
async def google_session(data: SessionIn):
    """Emergent-managed Google sign-in: exchange one-time session_id, then issue ROLLOW JWT.
    Only emails registered by the Owner may sign in (role comes from our DB)."""
    async with httpx.AsyncClient(timeout=15) as hc:
        r = await hc.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                         headers={"X-Session-ID": data.session_id})
    if r.status_code != 200:
        raise HTTPException(401, "Sesi Google tidak valid")
    email = r.json().get("email", "").lower()
    u = await db.users.find_one({"email": email}, {"_id": 0})
    if not u or not u.get("is_active", True):
        raise HTTPException(403, f"Email {email} belum terdaftar. Minta Owner menambahkan Anda di menu Karyawan.")
    token = make_token(u)
    return {"session_token": token, "access_token": token, "user": public_user(u)}


@api.get("/auth/me")
async def me(u=Depends(current_user)):
    return public_user(u)


@api.get("/users")
async def list_users(u=Depends(current_user)):
    if u["role"] not in PERM["users"] + PERM["payroll"] + PERM["attendance_all"]:
        raise HTTPException(403, "Akses ditolak")
    return [public_user(x) for x in await find("users", sort="name")]


@api.post("/users")
async def create_user(data: UserIn, u=Depends(need("users"))):
    if data.role not in ALL:
        raise HTTPException(400, "Role tidak valid")
    if await db.users.find_one({"email": data.email.lower()}):
        raise HTTPException(409, "Email sudah terdaftar")
    if not data.password or len(data.password) < 6:
        raise HTTPException(400, "Password minimal 6 karakter")
    d = data.model_dump()
    d["email"] = d["email"].lower()
    d["password_hash"] = hash_pw(d.pop("password"))
    return public_user(await insert("users", d))


@api.put("/users/{uid}")
async def update_user(uid: str, data: UserIn, u=Depends(need("users"))):
    d = data.model_dump()
    pw = d.pop("password")
    d["email"] = d["email"].lower()
    if pw:
        d["password_hash"] = hash_pw(pw)
    await db.users.update_one({"id": uid}, {"$set": d})
    return public_user(await db.users.find_one({"id": uid}, {"_id": 0}))


# ---------------- Ingredients & inventory ----------------
@api.get("/ingredients")
async def list_ingredients(u=Depends(current_user)):
    ings = await find("ingredients", sort="name")
    stocks = await find("stocks", sort="location")
    for i in ings:
        i["stock"] = {loc: 0.0 for loc in LOCATIONS}
        for s in stocks:
            if s["ingredient_id"] == i["id"]:
                i["stock"][s["location"]] = round(s["qty"], 2)
        i["total"] = round(sum(i["stock"].values()), 2)
        i["low"] = i["total"] < i.get("min_stock", 0)
    return sorted(ings, key=lambda x: x["name"])


@api.post("/ingredients")
async def create_ingredient(data: IngredientIn, u=Depends(need("menu_edit"))):
    return await insert("ingredients", data.model_dump())


@api.put("/ingredients/{iid}")
async def update_ingredient(iid: str, data: IngredientIn, u=Depends(need("menu_edit"))):
    await db.ingredients.update_one({"id": iid}, {"$set": data.model_dump()})
    return {"ok": True}


@api.get("/inventory/low-stock")
async def low_stock(u=Depends(current_user)):
    return [i for i in await list_ingredients(u) if i["low"]]


@api.post("/inventory/move")
async def inventory_move(data: MoveIn, u=Depends(need("inventory_move"))):
    if data.qty <= 0 or data.location not in LOCATIONS:
        raise HTTPException(400, "Data tidak valid")
    if data.type == "in":
        await move_stock(data.ingredient_id, data.location, data.qty, "stok_masuk", data.note, u)
        if data.total_cost > 0:
            await add_finance("expense", "Purchasing", data.total_cost, f"Stok masuk: {data.note}", "", u)
    elif data.type == "out":
        await move_stock(data.ingredient_id, data.location, -data.qty, "stok_keluar", data.note, u)
    elif data.type == "transfer":
        if data.to_location not in LOCATIONS or data.to_location == data.location:
            raise HTTPException(400, "Lokasi tujuan tidak valid")
        if await get_stock(data.ingredient_id, data.location) < data.qty:
            raise HTTPException(400, "Stok lokasi asal tidak cukup")
        await move_stock(data.ingredient_id, data.location, -data.qty, "transfer_keluar", f"ke {data.to_location}", u)
        await move_stock(data.ingredient_id, data.to_location, data.qty, "transfer_masuk", f"dari {data.location}", u)
    else:
        raise HTTPException(400, "Tipe tidak valid")
    return {"ok": True}


@api.get("/inventory/movements")
async def movements(u=Depends(need("inventory_view"))):
    return await find("stock_movements", limit=200)


# ---------------- Menu ----------------
@api.get("/menus")
async def list_menus(u=Depends(current_user)):
    imap = await ingredient_map()
    menus = await find("menus", sort="name")
    for m in menus:
        m["hpp"] = await menu_hpp(m, imap)
        m["margin"] = round(m["price"] - m["hpp"], 2)
        m["recipe_detail"] = [{**r, "name": imap.get(r["ingredient_id"], {}).get("name", "?"),
                               "unit": imap.get(r["ingredient_id"], {}).get("unit", "")} for r in m.get("recipe", [])]
    return sorted(menus, key=lambda x: (x["category"], x["name"]))


@api.post("/menus")
async def create_menu(data: MenuIn, u=Depends(need("menu_edit"))):
    return await insert("menus", data.model_dump())


@api.put("/menus/{mid}")
async def update_menu(mid: str, data: MenuIn, u=Depends(need("menu_edit"))):
    await db.menus.update_one({"id": mid}, {"$set": data.model_dump()})
    return {"ok": True}


# ---------------- Promo ----------------
async def active_promos():
    t = today()
    return [p for p in await find("promos", {"is_active": True}) if p["start_date"] <= t <= p["end_date"] and p["kind"] == "promo"]


@api.get("/promos")
async def list_promos(active: bool = False, u=Depends(current_user)):
    if active:
        return await active_promos()
    promos = await find("promos")
    for p in promos:
        sales = await find("sales", {"promo_id": p["id"], **VALID_SALE})
        p["usage"] = len(sales)
        p["revenue"] = round(sum(s["total"] for s in sales), 2)
        p["discount_given"] = round(sum(s["discount"] for s in sales), 2)
    return promos


@api.post("/promos")
async def create_promo(data: PromoIn, u=Depends(need("marketing"))):
    p = await insert("promos", data.model_dump())
    if data.budget > 0:
        await add_finance("expense", "Marketing", data.budget, f"Budget {data.kind}: {data.name}", p["id"], u)
    return p


@api.put("/promos/{pid}")
async def update_promo(pid: str, data: PromoIn, u=Depends(need("marketing"))):
    await db.promos.update_one({"id": pid}, {"$set": data.model_dump(exclude={"budget"})})
    return {"ok": True}


# ---------------- Settings (tax, loyalty, receipt) ----------------
DEFAULT_SETTINGS = {
    "tax_enabled": True, "tax_name": "PB1", "tax_percent": 10.0, "tax_default_on": True,
    "service_percent": 0.0,
    "loyalty_enabled": True, "points_per_nota": 1, "points_min_purchase": 0, "points_per_amount": 0,
    "receipt": {"cafe_name": "ROLLOW", "address": "", "phone": "", "header_note": "",
                "footer_note": "Terima kasih atas kunjungan Anda!", "wifi": "",
                "show_cashier": True, "show_customer": True, "show_points": True},
}


class SettingsIn(BaseModel):
    tax_enabled: bool
    tax_name: str
    tax_percent: float
    tax_default_on: bool
    service_percent: float = 0
    loyalty_enabled: bool
    points_per_nota: int
    points_min_purchase: float = 0
    points_per_amount: float = 0
    receipt: dict


async def get_settings():
    d = await db.settings.find_one({"outlet_id": OUTLET}, {"_id": 0})
    out = {**DEFAULT_SETTINGS, **(d or {})}
    out["receipt"] = {**DEFAULT_SETTINGS["receipt"], **((d or {}).get("receipt") or {})}
    return out


@api.get("/settings")
async def read_settings(u=Depends(current_user)):
    return await get_settings()


@api.put("/settings")
async def write_settings(data: SettingsIn, u=Depends(need("settings"))):
    await db.settings.update_one({"outlet_id": OUTLET}, {"$set": {**data.model_dump(), "outlet_id": OUTLET,
                                 "updated_by": u["name"], "updated_at": now().isoformat()}}, upsert=True)
    return await get_settings()


# ---------------- Customers / loyalty ----------------
class CustomerIn(BaseModel):
    name: str
    phone: str = ""


@api.get("/customers")
async def list_customers(q: str = "", u=Depends(need("customers"))):
    query = {"$or": [{"name": {"$regex": q, "$options": "i"}}, {"phone": {"$regex": q}}]} if q else {}
    return await find("customers", query, sort="points", limit=200)


@api.post("/customers")
async def create_customer(data: CustomerIn, u=Depends(need("pos"))):
    if data.phone and await db.customers.find_one({"phone": data.phone, "outlet_id": OUTLET}):
        raise HTTPException(409, "No. HP sudah terdaftar")
    return await insert("customers", {**data.model_dump(), "points": 0, "visits": 0, "total_spent": 0})


@api.get("/customers/{cid}/history")
async def customer_history(cid: str, u=Depends(need("customers"))):
    return await find("sales", {"customer_id": cid}, limit=100)


# ---------------- POS / Sales ----------------
VALID_SALE = {"status": {"$nin": ["void", "cancelled"]}}


@api.post("/sales")
async def create_sale(data: SaleIn, u=Depends(need("pos"))):
    if not data.items:
        raise HTTPException(400, "Keranjang kosong")
    st = await get_settings()
    imap = await ingredient_map()
    lines, subtotal, hpp_total = [], 0.0, 0.0
    usage = {}
    for it in data.items:
        m = await db.menus.find_one({"id": it.menu_id}, {"_id": 0})
        if not m:
            raise HTTPException(404, "Menu tidak ditemukan")
        hpp = await menu_hpp(m, imap)
        lines.append({"menu_id": m["id"], "name": m["name"], "qty": it.qty, "price": m["price"], "note": it.note,
                      "station": m.get("station") or m.get("location", "bar"),
                      "hpp": hpp, "subtotal": m["price"] * it.qty})
        subtotal += m["price"] * it.qty
        hpp_total += hpp * it.qty
        for r in m.get("recipe", []):
            key = (r["ingredient_id"], m.get("location", "bar"))
            usage[key] = usage.get(key, 0) + r["qty"] * it.qty
    discount, promo_name = 0.0, None
    if data.promo_id:
        p = await db.promos.find_one({"id": data.promo_id}, {"_id": 0})
        if p:
            discount = subtotal * p["value"] / 100 if p["discount_type"] == "percent" else min(p["value"], subtotal)
            promo_name = p["name"]
    base = subtotal - discount
    service = round(base * st["service_percent"] / 100, 2) if st["service_percent"] else 0.0
    tax = round((base + service) * st["tax_percent"] / 100, 2) if (st["tax_enabled"] and data.apply_tax) else 0.0
    total = round(base + service + tax, 2)
    cust, points = None, 0
    if data.customer_id:
        cust = await db.customers.find_one({"id": data.customer_id}, {"_id": 0})
        if cust and st["loyalty_enabled"] and total >= st["points_min_purchase"]:
            points = int(st["points_per_nota"]) + (int(total // st["points_per_amount"]) if st["points_per_amount"] else 0)
    count = await db.sales.count_documents({"date": today(), "outlet_id": OUTLET})
    sale = await insert("sales", {
        "number": f"RLW-{now().strftime('%y%m%d')}-{count + 1:04d}", "items": lines, "subtotal": subtotal,
        "discount": round(discount, 2), "promo_id": data.promo_id if promo_name else None, "promo_name": promo_name,
        "service": service, "tax": tax, "tax_name": st["tax_name"] if tax else None, "tax_percent": st["tax_percent"] if tax else 0,
        "total": total, "hpp": round(hpp_total, 2), "profit": round(base - hpp_total, 2),
        "payment_method": data.payment_method, "cash_received": data.cash_received,
        "customer": cust["name"] if cust else data.customer, "customer_id": cust["id"] if cust else None,
        "customer_phone": cust["phone"] if cust else "", "points_earned": points,
        "points_balance": (cust["points"] + points) if cust else None, "order_note": data.order_note,
        "time": now().strftime("%H:%M"), "status": "paid",
        "cashier_id": u["id"], "cashier_name": u["name"], "closed": False})
    # recipe -> auto deduct inventory
    for (iid, loc), q in usage.items():
        await move_stock(iid, loc, -q, "penjualan", sale["number"], u)
    # sale -> finance income (tax collected recorded separately as liability-like income line)
    await add_finance("income", "Penjualan", round(base + service, 2), f"Penjualan {sale['number']} ({data.payment_method})", sale["id"], u)
    if tax:
        await add_finance("income", f"Pajak {st['tax_name']}", tax, f"Pajak {sale['number']}", sale["id"], u)
    if cust:
        await db.customers.update_one({"id": cust["id"]}, {"$inc": {"points": points, "visits": 1, "total_spent": total}})
    return sale


class VoidIn(BaseModel):
    kind: str  # void | cancelled
    reason: str


@api.post("/sales/{sid}/void")
async def void_sale(sid: str, data: VoidIn, u=Depends(need("sales_void"))):
    s = await db.sales.find_one({"id": sid, "outlet_id": OUTLET}, {"_id": 0})
    if not s or s.get("status") in ["void", "cancelled"]:
        raise HTTPException(400, "Nota tidak ditemukan / sudah dibatalkan")
    if data.kind not in ["void", "cancelled"] or not data.reason.strip():
        raise HTTPException(400, "Isi alasan pembatalan")
    # reverse stock
    movs = await db.stock_movements.find({"ref": s["number"], "type": "penjualan", "outlet_id": OUTLET}, {"_id": 0}).to_list(500)
    for mv in movs:
        await move_stock(mv["ingredient_id"], mv["location"], -mv["qty"], f"{data.kind}_penjualan", s["number"], u)
    # reverse finance
    fins = await db.finance.find({"ref": sid, "type": "income", "outlet_id": OUTLET}, {"_id": 0}).to_list(10)
    for f in fins:
        await add_finance("income", f["category"], -f["amount"], f"{data.kind.upper()} {s['number']}: {data.reason}", sid, u)
    # reverse loyalty
    if s.get("customer_id"):
        await db.customers.update_one({"id": s["customer_id"]}, {"$inc": {"points": -s.get("points_earned", 0), "visits": -1, "total_spent": -s["total"]}})
    await db.sales.update_one({"id": sid}, {"$set": {"status": data.kind, "void_reason": data.reason,
                                                    "void_by": u["name"], "void_at": now().isoformat()}})
    return {"ok": True, "status": data.kind}


@api.get("/sales")
async def list_sales(date: Optional[str] = None, period: str = "day", status: str = "all", u=Depends(need("sales_view"))):
    d = date or today()
    q = {"date": {"$regex": f"^{d if period == 'day' else d[:7]}"}}
    if status != "all":
        q["status"] = status if status != "paid" else {"$nin": ["void", "cancelled"]}
    sales = await find("sales", q, limit=2000)
    valid = [x for x in sales if x.get("status", "paid") not in ["void", "cancelled"]]
    by = {}
    for x in valid:
        by[x["payment_method"]] = by.get(x["payment_method"], 0) + x["total"]
    recap = {"nota": len(valid), "void": len([x for x in sales if x.get("status") == "void"]),
             "cancelled": len([x for x in sales if x.get("status") == "cancelled"]),
             "subtotal": sum(x["subtotal"] for x in valid), "discount": sum(x["discount"] for x in valid),
             "tax": sum(x.get("tax", 0) for x in valid), "service": sum(x.get("service", 0) for x in valid),
             "total": sum(x["total"] for x in valid), "hpp": sum(x["hpp"] for x in valid),
             "profit": sum(x["profit"] for x in valid), "by_method": by}
    return {"recap": recap, "sales": sales}


@api.get("/pos/summary")
async def pos_summary(u=Depends(need("pos"))):
    sales = await find("sales", {"date": today(), "closed": False, **VALID_SALE})
    by = {}
    for s in sales:
        by[s["payment_method"]] = by.get(s["payment_method"], 0) + s["total"]
    return {"count": len(sales), "total": round(sum(s["total"] for s in sales), 2),
            "discount": round(sum(s["discount"] for s in sales), 2), "by_method": by,
            "closings": await find("register_closes", {"date": today()})}


@api.post("/pos/close")
async def pos_close(u=Depends(need("pos"))):
    summ = await pos_summary(u)
    if summ["count"] == 0:
        raise HTTPException(400, "Tidak ada transaksi untuk ditutup")
    summ.pop("closings")
    rec = await insert("register_closes", {**summ, "user_name": u["name"]})
    await db.sales.update_many({"date": today(), "closed": False, "outlet_id": OUTLET}, {"$set": {"closed": True}})
    return rec


# ---------------- Stock opname ----------------
@api.post("/opname")
async def create_opname(data: OpnameIn, u=Depends(need("opname"))):
    imap = await ingredient_map()
    lines = []
    for ln in data.lines:
        system = await get_stock(ln.ingredient_id, data.location)
        diff = round(ln.physical - system, 2)
        ing = imap.get(ln.ingredient_id, {})
        lines.append({"ingredient_id": ln.ingredient_id, "name": ing.get("name"), "unit": ing.get("unit"),
                      "system": round(system, 2), "physical": ln.physical, "diff": diff,
                      "diff_value": round(diff * ing.get("cost_per_unit", 0), 2)})
        if diff != 0:
            await move_stock(ln.ingredient_id, data.location, diff, "selisih_opname", "Stock opname", u)
    return await insert("opnames", {"location": data.location, "lines": lines, "note": data.note,
                                    "total_diff_value": round(sum(x["diff_value"] for x in lines), 2),
                                    "user_name": u["name"]})


@api.get("/opname")
async def list_opname(u=Depends(need("opname"))):
    return await find("opnames", limit=100)


# ---------------- Waste ----------------
@api.post("/waste")
async def create_waste(data: WasteIn, u=Depends(need("waste"))):
    ing = await db.ingredients.find_one({"id": data.ingredient_id}, {"_id": 0})
    if not ing or data.qty <= 0:
        raise HTTPException(400, "Data tidak valid")
    return await insert("wastes", {**data.model_dump(), "ingredient_name": ing["name"], "unit": ing["unit"],
                                   "value": round(data.qty * ing["cost_per_unit"], 2), "status": "pending",
                                   "user_name": u["name"]})


@api.get("/waste")
async def list_waste(u=Depends(need("waste"))):
    return await find("wastes", limit=200)


@api.post("/waste/{wid}/decide")
async def decide_waste(wid: str, data: DecisionIn, u=Depends(need("waste_approve"))):
    w = await db.wastes.find_one({"id": wid}, {"_id": 0})
    if not w or w["status"] != "pending":
        raise HTTPException(400, "Waste tidak ditemukan / sudah diproses")
    status = "approved" if data.approve else "rejected"
    await db.wastes.update_one({"id": wid}, {"$set": {"status": status, "approved_by": u["name"]}})
    if data.approve:
        await move_stock(w["ingredient_id"], w["location"], -w["qty"], "waste", w["reason"], u)
    return {"ok": True, "status": status}


# ---------------- Purchasing ----------------
@api.post("/purchasing")
async def create_pr(data: PRIn, u=Depends(need("purchase"))):
    imap = await ingredient_map()
    items = [{**i.model_dump(), "name": imap.get(i.ingredient_id, {}).get("name"),
              "unit": imap.get(i.ingredient_id, {}).get("unit"),
              "est_price": i.est_price or round(i.qty * imap.get(i.ingredient_id, {}).get("cost_per_unit", 0), 2)}
             for i in data.items]
    if not items:
        raise HTTPException(400, "Item kosong")
    count = await db.purchase_requests.count_documents({"outlet_id": OUTLET})
    return await insert("purchase_requests", {"number": f"PR-{count + 1:04d}", "items": items, "note": data.note,
                                              "est_total": round(sum(i["est_price"] for i in items), 2),
                                              "status": "pending", "requested_by": u["name"]})


@api.get("/purchasing")
async def list_pr(u=Depends(need("purchase"))):
    return await find("purchase_requests", limit=200)


@api.post("/purchasing/{pid}/decide")
async def decide_pr(pid: str, data: DecisionIn, u=Depends(need("purchase_approve"))):
    pr = await db.purchase_requests.find_one({"id": pid}, {"_id": 0})
    if not pr or pr["status"] != "pending":
        raise HTTPException(400, "PR tidak ditemukan / sudah diproses")
    status = "approved" if data.approve else "rejected"
    await db.purchase_requests.update_one({"id": pid}, {"$set": {"status": status, "approved_by": u["name"], "decision_note": data.note}})
    return {"ok": True, "status": status}


@api.post("/purchasing/{pid}/receive")
async def receive_pr(pid: str, data: ReceiveIn, u=Depends(need("purchase_receive"))):
    pr = await db.purchase_requests.find_one({"id": pid}, {"_id": 0})
    if not pr or pr["status"] != "approved":
        raise HTTPException(400, "PR belum disetujui")
    for i in pr["items"]:
        await move_stock(i["ingredient_id"], "gudang", i["qty"], "purchasing", pr["number"], u)
    paid = data.total_paid if data.total_paid is not None else pr["est_total"]
    await add_finance("expense", "Purchasing", paid, f"Pembelian {pr['number']}", pr["id"], u)
    await db.purchase_requests.update_one({"id": pid}, {"$set": {"status": "received", "total_paid": paid, "received_by": u["name"]}})
    return {"ok": True}


# ---------------- Finance ----------------
@api.post("/finance")
async def create_finance(data: FinanceIn, u=Depends(need("finance"))):
    if data.type not in ["income", "expense"] or data.amount <= 0:
        raise HTTPException(400, "Data tidak valid")
    return await add_finance(data.type, data.category, data.amount, data.note, "", u)


@api.get("/finance")
async def list_finance(month: Optional[str] = None, u=Depends(need("finance"))):
    m = month or today()[:7]
    return await db.finance.find({"outlet_id": OUTLET, "date": {"$regex": f"^{m}"}}, {"_id": 0}).sort("created_at", -1).to_list(2000)


# ---------------- Attendance ----------------
@api.post("/attendance")
async def create_attendance(data: AttendanceIn, u=Depends(current_user)):
    if data.type not in ["clock_in", "clock_out", "izin", "sakit", "libur", "lembur"]:
        raise HTTPException(400, "Tipe tidak valid")
    mine = await find("attendance", {"user_id": u["id"], "date": today()})
    types = [a["type"] for a in mine]
    if data.type == "clock_in" and "clock_in" in types:
        raise HTTPException(400, "Sudah clock in hari ini")
    if data.type == "clock_out" and ("clock_in" not in types or "clock_out" in types):
        raise HTTPException(400, "Belum clock in / sudah clock out")
    return await insert("attendance", {**data.model_dump(), "user_id": u["id"], "user_name": u["name"],
                                       "role": u["role"], "time": now().strftime("%H:%M")})


@api.get("/attendance")
async def list_attendance(all: bool = False, month: Optional[str] = None, u=Depends(current_user)):
    q = {"date": {"$regex": f"^{month or today()[:7]}"}}
    if not (all and u["role"] in PERM["attendance_all"]):
        q["user_id"] = u["id"]
    return await find("attendance", q, limit=1000)


# ---------------- Payroll ----------------
async def attendance_stats(uid, month):
    att = await find("attendance", {"user_id": uid, "date": {"$regex": f"^{month}"}})
    st = {t: len([a for a in att if a["type"] == t]) for t in ["clock_in", "izin", "sakit", "libur"]}
    st["lembur_hours"] = sum(a.get("hours", 0) for a in att if a["type"] == "lembur")
    return st


@api.post("/payroll")
async def create_payroll(data: PayrollIn, u=Depends(need("payroll"))):
    emp = await db.users.find_one({"id": data.user_id}, {"_id": 0})
    if not emp:
        raise HTTPException(404, "Karyawan tidak ditemukan")
    if await db.payrolls.find_one({"user_id": data.user_id, "month": data.month, "outlet_id": OUTLET}):
        raise HTTPException(409, "Payroll bulan ini sudah dibuat")
    st = await attendance_stats(data.user_id, data.month)
    overtime = st["lembur_hours"] * data.overtime_rate
    total = emp.get("base_salary", 0) + emp.get("allowance", 0) + data.bonus + overtime - data.deduction
    return await insert("payrolls", {"user_id": emp["id"], "name": emp["name"], "role": emp["role"],
                                     "month": data.month, "base_salary": emp.get("base_salary", 0),
                                     "allowance": emp.get("allowance", 0), "bonus": data.bonus,
                                     "overtime": overtime, "deduction": data.deduction, "attendance": st,
                                     "total": round(total, 2), "status": "draft"})


@api.get("/payroll")
async def list_payroll(month: Optional[str] = None, u=Depends(need("payroll"))):
    return await find("payrolls", {"month": month or today()[:7]})


@api.post("/payroll/{pid}/pay")
async def pay_payroll(pid: str, u=Depends(need("payroll"))):
    p = await db.payrolls.find_one({"id": pid}, {"_id": 0})
    if not p or p["status"] == "paid":
        raise HTTPException(400, "Payroll tidak valid / sudah dibayar")
    await add_finance("expense", "Gaji", p["total"], f"Gaji {p['name']} {p['month']}", pid, u)
    await db.payrolls.update_one({"id": pid}, {"$set": {"status": "paid", "paid_at": now().isoformat()}})
    return {"ok": True}


# ---------------- Dashboard ----------------
@api.get("/dashboard")
async def dashboard(u=Depends(current_user)):
    r, t, m = u["role"], today(), today()[:7]
    out = {"role": r, "date": t}
    if r in OPS + ["finance", "marketing"]:
        sales = await find("sales", {"date": t, **VALID_SALE})
        out["sales_today"] = round(sum(s["total"] for s in sales), 2)
        out["trx_today"] = len(sales)
        out["profit_today"] = round(sum(s["profit"] for s in sales), 2)
    if r in OPS:
        low = await low_stock(u)
        out["low_stock"] = [{"name": i["name"], "total": i["total"], "min": i["min_stock"], "unit": i["unit"]} for i in low]
    if r in MGMT:
        out["pending_waste"] = await db.wastes.count_documents({"status": "pending", "outlet_id": OUTLET})
        out["pending_pr"] = await db.purchase_requests.count_documents({"status": "pending", "outlet_id": OUTLET})
        out["approved_pr"] = await db.purchase_requests.count_documents({"status": "approved", "outlet_id": OUTLET})
    if r in ["owner", "finance"]:
        fin = await list_finance(m, u)
        inc = sum(f["amount"] for f in fin if f["type"] == "income")
        exp = sum(f["amount"] for f in fin if f["type"] == "expense")
        out["finance_month"] = {"income": round(inc, 2), "expense": round(exp, 2), "net": round(inc - exp, 2)}
    if r in PERM["marketing"]:
        out["active_promos"] = len(await active_promos())
    mine = await find("attendance", {"user_id": u["id"], "date": t})
    out["my_attendance"] = [a["type"] for a in mine]
    return out


# ---------------- Reports ----------------
def rng(period, date):
    d = date or today()
    return d if period == "day" else d[:7]


@api.get("/reports/{rtype}")
async def report(rtype: str, period: str = "day", date: Optional[str] = None, u=Depends(current_user)):
    if rtype not in REPORTS:
        raise HTTPException(404, "Laporan tidak ada")
    if u["role"] not in REPORTS[rtype]:
        raise HTTPException(403, "Akses ditolak")
    p = rng(period, date)
    q = {"date": {"$regex": f"^{p}"}}
    S, rows = {}, []
    if rtype == "sales":
        sales = await find("sales", {**q, **VALID_SALE})
        items = {}
        for s in sales:
            for i in s["items"]:
                it = items.setdefault(i["name"], {"qty": 0, "omzet": 0})
                it["qty"] += i["qty"]
                it["omzet"] += i["subtotal"]
        omzet = sum(s["total"] for s in sales)
        hpp = sum(s["hpp"] for s in sales)
        S = {"Transaksi": len(sales), "Omzet": omzet, "Diskon": sum(s["discount"] for s in sales),
             "Pajak": sum(s.get("tax", 0) for s in sales), "HPP": hpp, "Laba Kotor": omzet - hpp - sum(s.get("tax", 0) for s in sales),
             "Void/Batal": await db.sales.count_documents({**q, "outlet_id": OUTLET, "status": {"$in": ["void", "cancelled"]}})}
        for pm in set(s["payment_method"] for s in sales):
            S[f"Bayar {pm}"] = sum(s["total"] for s in sales if s["payment_method"] == pm)
        rows = [{"title": k, "subtitle": f"{v['qty']} terjual", "value": v["omzet"]} for k, v in sorted(items.items(), key=lambda x: -x[1]["omzet"])]
    elif rtype == "nota":
        allsales = await find("sales", q, limit=5000)
        valid = [x for x in allsales if x.get("status", "paid") not in ["void", "cancelled"]]
        S = {"Transaksi": len(valid), "Void/Batal": len(allsales) - len(valid), "Omzet": sum(x["total"] for x in valid),
             "Pajak": sum(x.get("tax", 0) for x in valid), "Diskon": sum(x["discount"] for x in valid)}
        rows = [{"title": f"{x['number']} · {x.get('time', '')}", "flag": x.get("status") in ["void", "cancelled"],
                 "subtitle": f"{x.get('status', 'paid').upper()} · {x['payment_method']} · {x.get('customer') or '-'} · {sum(i['qty'] for i in x['items'])} item · {x['cashier_name']}",
                 "value": x["total"]} for x in allsales]
    elif rtype == "inventory":
        ings = await list_ingredients(u)
        S = {"Total Bahan": len(ings), "Stok Rendah": len([i for i in ings if i["low"]]),
             "Nilai Stok": round(sum(i["total"] * i["cost_per_unit"] for i in ings), 2)}
        rows = [{"title": i["name"], "subtitle": f"G {i['stock']['gudang']} · B {i['stock']['bar']} · K {i['stock']['kitchen']} {i['unit']} (min {i['min_stock']})",
                 "value": round(i["total"] * i["cost_per_unit"], 2), "flag": i["low"]} for i in ings]
    elif rtype == "opname":
        ops = await find("opnames", q)
        agg = {}
        for o in ops:
            for ln in o["lines"]:
                a = agg.setdefault(ln["name"], {"diff": 0, "value": 0, "unit": ln["unit"]})
                a["diff"] += ln["diff"]
                a["value"] += ln["diff_value"]
        S = {"Jumlah Opname": len(ops), "Total Nilai Selisih": round(sum(o["total_diff_value"] for o in ops), 2)}
        rows = [{"title": k, "subtitle": f"Selisih {round(v['diff'], 2)} {v['unit']}", "value": round(v["value"], 2), "flag": v["diff"] < 0}
                for k, v in agg.items() if v["diff"] != 0]
    elif rtype == "waste":
        ws = await find("wastes", q)
        ap = [w for w in ws if w["status"] == "approved"]
        S = {"Total Catatan": len(ws), "Disetujui": len(ap), "Nilai Waste": round(sum(w["value"] for w in ap), 2)}
        rows = [{"title": w["ingredient_name"], "subtitle": f"{w['qty']} {w['unit']} · {w['reason']} · {w['location']} · {w['status']}", "value": w["value"]} for w in ws]
    elif rtype == "purchasing":
        prs = await find("purchase_requests", q)
        S = {"Total PR": len(prs), "Pending": len([x for x in prs if x["status"] == "pending"]),
             "Diterima": len([x for x in prs if x["status"] == "received"]),
             "Total Dibayar": round(sum(x.get("total_paid", 0) for x in prs), 2)}
        rows = [{"title": x["number"], "subtitle": f"{x['status']} · {x['requested_by']}", "value": x.get("total_paid", x["est_total"])} for x in prs]
    elif rtype == "finance":
        fin = await find("finance", q, limit=5000)
        inc = sum(f["amount"] for f in fin if f["type"] == "income")
        exp = sum(f["amount"] for f in fin if f["type"] == "expense")
        sales = await find("sales", {**q, **VALID_SALE})
        hpp = sum(s["hpp"] for s in sales)
        S = {"Pemasukan": inc, "Pengeluaran": exp, "Cash Flow Bersih": inc - exp, "HPP Terjual": hpp,
             "Laba Kotor (Omzet-HPP)": sum(s["total"] for s in sales) - hpp}
        cats = {}
        for f in fin:
            k = (f["type"], f["category"])
            cats[k] = cats.get(k, 0) + f["amount"]
        rows = [{"title": c, "subtitle": "Pemasukan" if t == "income" else "Pengeluaran", "value": v if t == "income" else -v} for (t, c), v in cats.items()]
    elif rtype == "payroll":
        ps = await find("payrolls", {"month": p[:7]})
        S = {"Karyawan": len(ps), "Total Gaji": sum(x["total"] for x in ps), "Sudah Dibayar": sum(x["total"] for x in ps if x["status"] == "paid")}
        rows = [{"title": x["name"], "subtitle": f"{x['role']} · {x['status']}", "value": x["total"]} for x in ps]
    elif rtype == "attendance":
        att = await find("attendance", q)
        S = {t: len([a for a in att if a["type"] == t]) for t in ["clock_in", "clock_out", "izin", "sakit", "libur", "lembur"]}
        rows = [{"title": a["user_name"], "subtitle": f"{a['date']} {a['time']} · {a['type']}", "value": None} for a in att]
    elif rtype == "marketing":
        promos = await list_promos(False, u)
        S = {"Promo/Campaign": len(promos), "Total Penggunaan": sum(x["usage"] for x in promos),
             "Omzet dari Promo": sum(x["revenue"] for x in promos), "Total Diskon": sum(x["discount_given"] for x in promos)}
        rows = [{"title": x["name"], "subtitle": f"{x['kind']} · {x['usage']}x dipakai · diskon {x['discount_given']}", "value": x["revenue"]} for x in promos]
    return {"type": rtype, "period": period, "range": p, "summary": S, "rows": rows}


# ---------------- Seed ----------------
@app.on_event("startup")
async def seed():
    await db.users.create_index("email", unique=True)
    pw = os.environ["DEMO_PASSWORD"]
    owner_email = os.environ["OWNER_EMAIL"].lower()
    if not await db.users.find_one({"email": owner_email}):
        await insert("users", {"email": owner_email, "password_hash": hash_pw(os.environ["OWNER_PASSWORD"]), "name": "Owner ROLLOW",
                               "role": "owner", "position": "Owner", "base_salary": 0, "allowance": 0, "is_active": True})
    demo = [("manager", "Rina Manager", 7000000), ("spv", "Budi Supervisor", 5500000), ("finance", "Sari Finance", 5500000),
            ("marketing", "Dewi Marketing", 5000000), ("crew", "Andi Crew", 3500000)]
    for key, name, sal in demo:
        email = f"{key}@rollow.id"
        if not await db.users.find_one({"email": email}):
            role = "supervisor" if key == "spv" else key
            await insert("users", {"email": email, "password_hash": hash_pw(pw), "name": name, "role": role,
                                   "position": name.split()[1], "base_salary": sal, "allowance": 500000, "is_active": True})
    if await db.ingredients.count_documents({}) == 0:
        ings = [("Gula", "gram", 15, 5000, [8000, 1700, 0]), ("Teh Celup", "pcs", 300, 50, [200, 40, 0]),
                ("Kopi Arabika", "gram", 250, 1000, [3000, 800, 0]), ("Susu UHT", "ml", 20, 3000, [10000, 2000, 0]),
                ("Es Batu", "gram", 1, 5000, [0, 10000, 0]), ("Roti Tawar", "pcs", 1500, 20, [40, 0, 15]),
                ("Telur", "pcs", 2200, 30, [60, 0, 20]), ("Kentang Beku", "gram", 40, 2000, [5000, 0, 1500]),
                ("Minyak Goreng", "ml", 18, 2000, [5000, 0, 1000]), ("Coklat Bubuk", "gram", 120, 500, [1500, 300, 0])]
        ids = {}
        sys_user = {"name": "System"}
        for n, unit, cost, mn, stocks in ings:
            d = await insert("ingredients", {"name": n, "unit": unit, "cost_per_unit": cost, "min_stock": mn, "category": "Bahan"})
            ids[n] = d["id"]
            for loc, q in zip(LOCATIONS, stocks):
                if q:
                    await move_stock(d["id"], loc, q, "saldo_awal", "Seed", sys_user)
        menus = [("Es Teh Manis", "Minuman", 8000, "bar", [("Teh Celup", 1), ("Gula", 20), ("Es Batu", 150)]),
                 ("Kopi Susu ROLLOW", "Minuman", 22000, "bar", [("Kopi Arabika", 18), ("Susu UHT", 150), ("Gula", 15), ("Es Batu", 150)]),
                 ("Americano", "Minuman", 18000, "bar", [("Kopi Arabika", 18), ("Es Batu", 150)]),
                 ("Coklat Panas", "Minuman", 20000, "bar", [("Coklat Bubuk", 30), ("Susu UHT", 200), ("Gula", 10)]),
                 ("Roti Bakar Telur", "Makanan", 25000, "kitchen", [("Roti Tawar", 2), ("Telur", 1), ("Minyak Goreng", 10)]),
                 ("French Fries", "Snack", 18000, "kitchen", [("Kentang Beku", 150), ("Minyak Goreng", 50)])]
        for n, cat, price, loc, rec in menus:
            await insert("menus", {"name": n, "category": cat, "price": price, "location": loc, "is_active": True,
                                   "recipe": [{"ingredient_id": ids[i], "qty": q} for i, q in rec]})
        await insert("promos", {"name": "Happy Hour 10%", "kind": "promo", "discount_type": "percent", "value": 10,
                                "start_date": today()[:8] + "01", "end_date": (now() + timedelta(days=60)).strftime("%Y-%m-%d"),
                                "description": "Diskon 10% semua menu", "budget": 0, "is_active": True})


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
logging.basicConfig(level=logging.INFO)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
