import { useMemo, useState } from "react";
import { FlatList, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, num, rp, useApi } from "@/src/api";
import { usesNativeTabs } from "@/src/navigation";
import { Btn, Card, Chips, Header, Icon, Page, rad, Sheet, sp, Stat, StateView, useStyles, useToast, useWide } from "@/src/ui";
import { makeStyles, useTheme } from "@/src/theme";

const METHODS = ["Cash", "QRIS", "Transfer", "Debit"].map((m) => ({ label: m, value: m }));

export default function POS() {
  const s = useStyles();
  const p = useP();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const wide = useWide();
  const toast = useToast();
  const bottomChrome = usesNativeTabs ? insets.bottom : 0;
  const { data: menus, loading, error, reload } = useApi<any[]>("/menus");
  const { data: promos } = useApi<any[]>("/promos?active=true");
  const [cat, setCat] = useState("all");
  const [cart, setCart] = useState<Record<string, number>>({});
  const [method, setMethod] = useState("Cash");
  const [promo, setPromo] = useState("none");
  const [cash, setCash] = useState("");
  const [cartOpen, setCartOpen] = useState(false);
  const [receipt, setReceipt] = useState<any>(null);
  const [closeOpen, setCloseOpen] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const active = (menus || []).filter((m) => m.is_active);
  const cats = useMemo(() => [{ label: "Semua", value: "all" }, ...Array.from(new Set(active.map((m) => m.category))).map((c) => ({ label: c, value: c }))], [menus]);
  const shown = cat === "all" ? active : active.filter((m) => m.category === cat);
  const lines = active.filter((m) => cart[m.id]).map((m) => ({ ...m, qty: cart[m.id] }));
  const subtotal = lines.reduce((a, l) => a + l.price * l.qty, 0);
  const pr = (promos || []).find((x) => x.id === promo);
  const discount = pr ? (pr.discount_type === "percent" ? (subtotal * pr.value) / 100 : Math.min(pr.value, subtotal)) : 0;
  const total = subtotal - discount;
  const count = lines.reduce((a, l) => a + l.qty, 0);

  const add = (id: string, d: number) => setCart((c) => {
    const n = { ...c, [id]: (c[id] || 0) + d };
    if (n[id] <= 0) delete n[id];
    return n;
  });

  const pay = async () => {
    setBusy(true);
    try {
      const sale = await api("/sales", { body: { items: lines.map((l) => ({ menu_id: l.id, qty: l.qty })), payment_method: method, promo_id: pr?.id ?? null } });
      setReceipt({ ...sale, cash: method === "Cash" ? num(cash) : 0 });
      setCart({});
      setCash("");
      setPromo("none");
      setCartOpen(false);
      toast("Transaksi berhasil, stok terpotong otomatis");
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const openClose = async () => {
    setCloseOpen(true);
    try {
      setSummary(await api("/pos/summary"));
    } catch (e: any) {
      toast(e.message, "error");
    }
  };
  const doClose = async () => {
    setBusy(true);
    try {
      await api("/pos/close", { body: {} });
      toast("Kasir ditutup");
      setCloseOpen(false);
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const CartPanel = (
    <View style={{ gap: sp.md }}>
      {lines.length === 0 && <Text style={s.muted}>Keranjang kosong</Text>}
      {lines.map((l) => (
        <View key={l.id} style={[s.row, { justifyContent: "space-between" }]}>
          <View style={{ flex: 1 }}>
            <Text style={s.title} numberOfLines={1}>{l.name}</Text>
            <Text style={s.sub}>{rp(l.price * l.qty)}</Text>
          </View>
          <Pressable testID={`cart-minus-${l.id}`} style={p.step} onPress={() => add(l.id, -1)}><Icon name="remove" size={20} color={colors.onSurface} /></Pressable>
          <Text style={[s.value, { minWidth: 24, textAlign: "center" }]}>{l.qty}</Text>
          <Pressable testID={`cart-plus-${l.id}`} style={p.step} onPress={() => add(l.id, 1)}><Icon name="add" size={20} color={colors.onSurface} /></Pressable>
        </View>
      ))}
      <Text style={s.section}>Promo</Text>
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="promo-chip" value={promo} onChange={setPromo} options={[{ label: "Tanpa Promo", value: "none" }, ...(promos || []).map((x) => ({ label: x.name, value: x.id }))]} />
      </View>
      <Text style={s.section}>Pembayaran</Text>
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="pay-method" value={method} onChange={setMethod} options={METHODS} />
      </View>
      {method === "Cash" && (
        <TextInput testID="cash-received-input" placeholder="Uang diterima (opsional)" placeholderTextColor={colors.muted} keyboardType="numeric" value={cash} onChangeText={setCash} style={p.input} />
      )}
      <View style={[s.row, { justifyContent: "space-between" }]}><Text style={s.sub}>Subtotal</Text><Text style={s.title}>{rp(subtotal)}</Text></View>
      {discount > 0 && <View style={[s.row, { justifyContent: "space-between" }]}><Text style={s.sub}>Diskon</Text><Text style={[s.title, { color: colors.success }]}>-{rp(discount)}</Text></View>}
      <View style={[s.row, { justifyContent: "space-between" }]}><Text style={s.title}>Total</Text><Text style={[s.value, { fontSize: 22, color: colors.brandPrimary }]} testID="cart-total-text">{rp(total)}</Text></View>
      <Btn title={`Bayar ${rp(total)}`} icon="checkmark-circle-outline" testID="pay-button" loading={busy} disabled={!lines.length} onPress={pay} />
    </View>
  );

  return (
    <Page>
      <Header title="Kasir" subtitle="Point of Sale" right={<Btn small variant="secondary" title="Tutup Kasir" icon="lock-closed-outline" testID="close-register-button" onPress={openClose} />} />
      <Chips testPrefix="pos-category" value={cat} onChange={setCat} options={cats} />
      <View style={{ flex: 1, flexDirection: "row" }}>
        <View style={{ flex: 1 }}>
          {!menus ? (
            <StateView loading={loading} error={error} onRetry={reload} />
          ) : (
            <FlatList
              key={wide ? "w" : "n"}
              data={shown}
              numColumns={wide ? 3 : 2}
              keyExtractor={(m) => m.id}
              columnWrapperStyle={{ gap: sp.md }}
              contentContainerStyle={{ padding: sp.lg, gap: sp.md, paddingBottom: (wide ? 0 : 88) + bottomChrome + sp.lg }}
              ListEmptyComponent={<StateView empty="Belum ada menu di kategori ini" />}
              renderItem={({ item }) => (
                <Pressable testID={`menu-item-${item.id}`} onPress={() => add(item.id, 1)} style={({ pressed }) => [p.item, cart[item.id] && p.itemActive, pressed && { transform: [{ scale: 0.97 }] }]}>
                  <Text style={s.sub}>{item.category}</Text>
                  <Text style={s.title} numberOfLines={2}>{item.name}</Text>
                  <View style={[s.row, { justifyContent: "space-between", marginTop: "auto" }]}>
                    <Text style={[s.value, { color: colors.brandPrimary }]}>{rp(item.price)}</Text>
                    {!!cart[item.id] && <View style={p.qtyBadge}><Text style={{ color: colors.onBrandPrimary, fontWeight: "800" }}>{cart[item.id]}</Text></View>}
                  </View>
                </Pressable>
              )}
            />
          )}
        </View>
        {wide && (
          <ScrollView style={p.side} contentContainerStyle={{ padding: sp.lg }}>
            <Text style={[s.title, { fontSize: 20, marginBottom: sp.md }]}>Pesanan</Text>
            {CartPanel}
          </ScrollView>
        )}
      </View>
      {!wide && count > 0 && (
        <Pressable testID="open-cart-button" onPress={() => setCartOpen(true)} style={[p.cartBar, { bottom: bottomChrome + sp.lg }]}>
          <Icon name="cart" size={22} color={colors.onBrandPrimary} />
          <Text style={p.cartText}>{count} item</Text>
          <Text style={[p.cartText, { marginLeft: "auto" }]}>{rp(total)}</Text>
          <Icon name="chevron-up" size={20} color={colors.onBrandPrimary} />
        </Pressable>
      )}
      <Sheet visible={cartOpen} onClose={() => setCartOpen(false)} title="Pesanan" testID="cart-sheet">{CartPanel}</Sheet>
      <Sheet visible={!!receipt} onClose={() => setReceipt(null)} title="Struk" testID="receipt-sheet">
        {receipt && (
          <Card>
            <Text style={[s.title, { textAlign: "center", fontSize: 20 }]}>ROLLOW</Text>
            <Text style={[s.sub, { textAlign: "center" }]} testID="receipt-number">{receipt.number} · {receipt.cashier_name}</Text>
            <View style={{ height: 1, backgroundColor: colors.border, marginVertical: sp.md }} />
            {receipt.items.map((i: any) => (
              <View key={i.menu_id} style={[s.row, { justifyContent: "space-between" }]}>
                <Text style={{ color: colors.onSurface }}>{i.qty}x {i.name}</Text>
                <Text style={{ color: colors.onSurface }}>{rp(i.subtotal)}</Text>
              </View>
            ))}
            <View style={{ height: 1, backgroundColor: colors.border, marginVertical: sp.md }} />
            {receipt.discount > 0 && <Text style={s.sub}>Diskon ({receipt.promo_name}): -{rp(receipt.discount)}</Text>}
            <Text style={s.value}>Total {rp(receipt.total)}</Text>
            <Text style={s.sub}>Bayar: {receipt.payment_method}</Text>
            {receipt.cash > 0 && <Text style={s.sub}>Tunai {rp(receipt.cash)} · Kembali {rp(receipt.cash - receipt.total)}</Text>}
          </Card>
        )}
        <Btn title="Transaksi Baru" style={{ marginTop: sp.lg }} testID="receipt-done-button" onPress={() => setReceipt(null)} />
      </Sheet>
      <Sheet visible={closeOpen} onClose={() => setCloseOpen(false)} title="Tutup Kasir" testID="close-register-sheet">
        {!summary ? <StateView loading /> : (
          <View style={{ gap: sp.md }}>
            <View style={s.wrap}>
              <Stat label="Transaksi" value={String(summary.count)} testID="close-count" />
              <Stat label="Total" value={rp(summary.total)} tone="brand" testID="close-total" />
            </View>
            {Object.entries(summary.by_method).map(([k, v]: any) => (
              <View key={k} style={[s.row, { justifyContent: "space-between" }]}><Text style={s.sub}>{k}</Text><Text style={s.title}>{rp(v)}</Text></View>
            ))}
            {summary.closings.length > 0 && <Text style={s.sub}>Sudah ditutup {summary.closings.length}x hari ini</Text>}
            <Btn title="Tutup Kasir Sekarang" variant="danger" testID="confirm-close-register-button" loading={busy} disabled={!summary.count} onPress={doClose} />
          </View>
        )}
      </Sheet>
    </Page>
  );
}

const useP = makeStyles((c) => ({
  item: { flex: 1, minHeight: 120, backgroundColor: c.surfaceSecondary, borderRadius: rad.md, borderWidth: 1, borderColor: c.border, padding: sp.md, gap: sp.xs },
  itemActive: { borderColor: c.brandPrimary, backgroundColor: c.brandTertiary },
  qtyBadge: { backgroundColor: c.brandPrimary, minWidth: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  step: { width: 44, height: 44, borderRadius: rad.sm, backgroundColor: c.surfaceTertiary, alignItems: "center", justifyContent: "center" },
  input: { minHeight: 48, borderRadius: rad.md, borderWidth: 1, borderColor: c.border, backgroundColor: c.surfaceSecondary, paddingHorizontal: sp.md, fontSize: 15, color: c.onSurface },
  side: { width: 360, flexGrow: 0, borderLeftWidth: 1, borderLeftColor: c.border, backgroundColor: c.surface },
  cartBar: { position: "absolute", left: sp.lg, right: sp.lg, height: 56, borderRadius: rad.md, backgroundColor: c.brandPrimary, flexDirection: "row", alignItems: "center", gap: sp.sm, paddingHorizontal: sp.lg },
  cartText: { color: c.onBrandPrimary, fontWeight: "800", fontSize: 16 },
}));
