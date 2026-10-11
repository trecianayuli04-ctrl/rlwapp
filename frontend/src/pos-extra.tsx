import { useState } from "react";
import { Image, Pressable, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";

import { api, num, rp, useApi } from "@/src/api";
import { Btn, Card, Chips, Field, Sheet, sp, useStyles, useToast } from "@/src/ui";
import { useTheme } from "@/src/theme";

// ---------- Kas Keluar (petty cash dari kasir, dengan foto bukti) ----------
export function PettyCashSheet({ visible, onClose, onDone }: { visible: boolean; onClose: () => void; onDone?: () => void }) {
  const s = useStyles();
  const toast = useToast();
  const { data: cats } = useApi<any[]>(visible ? "/config/expense_categories?active=true" : null);
  const { data: methods } = useApi<any[]>(visible ? "/config/payment_methods?active=true" : null);
  const [cat, setCat] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [method, setMethod] = useState("Cash");
  const [photo, setPhoto] = useState("");
  const [busy, setBusy] = useState(false);
  const catList = (cats || []).map((c) => ({ label: c.name, value: c.name }));

  const pick = async (camera: boolean) => {
    const perm = camera ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return toast("Izin kamera/galeri ditolak", "error");
    const res = camera
      ? await ImagePicker.launchCameraAsync({ base64: true, quality: 0.5, mediaTypes: ["images"] })
      : await ImagePicker.launchImageLibraryAsync({ base64: true, quality: 0.5, mediaTypes: ["images"] });
    if (!res.canceled && res.assets?.[0]?.base64) setPhoto(`data:image/jpeg;base64,${res.assets[0].base64}`);
  };
  const submit = async () => {
    setBusy(true);
    try {
      const pocket = (cats || []).find((c) => c.name === cat)?.pocket_id || null;
      const r = await api<any>("/expenses", { body: { category: cat || catList[0]?.value, amount: num(amount), note, method, pocket_id: pocket, photo, source: "kasir" } });
      toast(r.pending ? "Pengeluaran diajukan, menunggu persetujuan" : "Kas keluar dicatat & saldo diperbarui");
      setAmount(""); setNote(""); setPhoto("");
      onClose();
      onDone?.();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet visible={visible} onClose={onClose} title="Kas Keluar (Pengeluaran)" testID="petty-sheet">
      <Text style={[s.sub, { marginBottom: sp.sm }]}>Catat pengeluaran kas kecil (mis. beli es batu). Tercatat otomatis di keuangan, kasir & audit.</Text>
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="petty-cat" value={cat || catList[0]?.value || ""} onChange={setCat} options={catList} />
      </View>
      <Field label="Nominal (Rp)" testID="petty-amount-input" keyboardType="numeric" value={amount} onChangeText={setAmount} />
      <Field label="Keterangan / alasan" testID="petty-note-input" value={note} onChangeText={setNote} />
      <Text style={s.label}>Sumber dana</Text>
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="petty-method" value={method} onChange={setMethod} options={(methods || []).map((m) => ({ label: m.name, value: m.name }))} />
      </View>
      <View style={[s.row, { marginVertical: sp.md }]}>
        <Btn title="Kamera" variant="secondary" icon="camera-outline" style={{ flex: 1 }} testID="petty-camera-button" onPress={() => pick(true)} />
        <Btn title="Galeri" variant="secondary" icon="image-outline" style={{ flex: 1 }} testID="petty-gallery-button" onPress={() => pick(false)} />
      </View>
      {!!photo && <Image source={{ uri: photo }} style={{ width: "100%", height: 160, borderRadius: 12, marginBottom: sp.md }} resizeMode="cover" />}
      <Btn title="Simpan Pengeluaran" testID="petty-submit-button" loading={busy} disabled={!num(amount) || !(cat || catList[0]?.value)} onPress={submit} />
    </Sheet>
  );
}

// ---------- Pesanan App (ShopeeFood/GoFood/GrabFood) dengan harga khusus platform ----------
export function ExternalOrderSheet({ visible, onClose, menus, onDone }: { visible: boolean; onClose: () => void; menus: any[]; onDone?: (sale: any) => void }) {
  const s = useStyles();
  const { colors } = useTheme();
  const toast = useToast();
  const { data: platforms } = useApi<any[]>(visible ? "/config/platforms?active=true" : null);
  const [platform, setPlatform] = useState("");
  const [orderNo, setOrderNo] = useState("");
  const [lines, setLines] = useState<any[]>([]);
  const [discount, setDiscount] = useState("");
  const [comm, setComm] = useState("");
  const [status, setStatus] = useState("pending");
  const [manualName, setManualName] = useState("");
  const [manualPrice, setManualPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const plat = (platforms || []).find((p) => p.name === (platform || platforms?.[0]?.name));
  const active = (menus || []).filter((m) => m.is_active);

  const addMenu = (m: any) => setLines((l) => (l.find((x) => x.menu_id === m.id) ? l : [...l, { menu_id: m.id, name: m.name, qty: 1, price: String(m.price) }]));
  const addManual = () => {
    if (!manualName.trim() || !num(manualPrice)) return;
    setLines((l) => [...l, { menu_id: null, name: manualName, qty: 1, price: manualPrice }]);
    setManualName(""); setManualPrice("");
  };
  const upd = (i: number, k: string, v: any) => setLines((l) => l.map((x, idx) => (idx === i ? { ...x, [k]: v } : x)));
  const rm = (i: number) => setLines((l) => l.filter((_, idx) => idx !== i));
  const gross = lines.reduce((a, l) => a + num(String(l.price)) * (Number(l.qty) || 0), 0);
  const commPct = comm !== "" ? num(comm) : plat?.commission_percent || 0;
  const commission = (gross * commPct) / 100;
  const net = gross - commission - num(discount);

  const submit = async () => {
    setBusy(true);
    try {
      const sale = await api<any>("/external-sales", {
        body: {
          platform: platform || platforms?.[0]?.name, order_no: orderNo,
          items: lines.map((l) => ({ menu_id: l.menu_id, name: l.name, qty: Number(l.qty) || 1, price: num(String(l.price)) })),
          discount: num(discount), commission_percent: comm !== "" ? num(comm) : null, payment_status: status,
        },
      });
      toast("Pesanan eksternal tercatat & stok terpotong");
      setLines([]); setOrderNo(""); setDiscount(""); setComm("");
      onClose();
      onDone?.(sale);
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet visible={visible} onClose={onClose} title="Pesanan Aplikasi Eksternal" testID="external-sheet">
      <Text style={[s.sub, { marginBottom: sp.sm }]}>Harga khusus platform tidak mengubah harga reguler menu. Nomor pesanan mencegah duplikasi.</Text>
      <Text style={s.label}>Platform</Text>
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="ext-platform" value={platform || platforms?.[0]?.name || ""} onChange={setPlatform} options={(platforms || []).map((p) => ({ label: p.name, value: p.name }))} />
      </View>
      <Field label="Nomor pesanan (opsional)" testID="ext-orderno-input" value={orderNo} onChangeText={setOrderNo} />
      <Text style={s.section}>Item Pesanan</Text>
      {lines.map((l, i) => (
        <Card key={i} style={{ marginBottom: sp.sm }}>
          <View style={[s.row, { justifyContent: "space-between" }]}>
            <Text style={[s.title, { flex: 1, fontSize: 14 }]}>{l.name}</Text>
            <Pressable testID={`ext-rm-${i}`} hitSlop={8} onPress={() => rm(i)}><Text style={{ color: colors.error }}>Hapus</Text></Pressable>
          </View>
          <View style={s.row}>
            <View style={{ flex: 1 }}><Field label="Qty" testID={`ext-qty-${i}`} keyboardType="numeric" value={String(l.qty)} onChangeText={(t) => upd(i, "qty", t.replace(/[^0-9]/g, ""))} /></View>
            <View style={{ flex: 2 }}><Field label="Harga platform (Rp)" testID={`ext-price-${i}`} keyboardType="numeric" value={String(l.price)} onChangeText={(t) => upd(i, "price", t)} /></View>
          </View>
        </Card>
      ))}
      <Text style={s.label}>Tambah dari menu</Text>
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="ext-menu" value="" onChange={(id) => { const m = active.find((x) => x.id === id); if (m) addMenu(m); }} options={active.map((m) => ({ label: m.name, value: m.id }))} />
      </View>
      <View style={[s.row, { marginTop: sp.sm }]}>
        <View style={{ flex: 2 }}><Field label="Item manual (nama)" testID="ext-manual-name" value={manualName} onChangeText={setManualName} /></View>
        <View style={{ flex: 1 }}><Field label="Harga" testID="ext-manual-price" keyboardType="numeric" value={manualPrice} onChangeText={setManualPrice} /></View>
      </View>
      <Btn title="+ Tambah Item Manual" variant="ghost" small testID="ext-add-manual" onPress={addManual} />
      <View style={[s.row, { marginTop: sp.md }]}>
        <View style={{ flex: 1 }}><Field label="Diskon ditanggung outlet (Rp)" testID="ext-discount-input" keyboardType="numeric" value={discount} onChangeText={setDiscount} /></View>
        <View style={{ flex: 1 }}><Field label={`Komisi % (default ${plat?.commission_percent || 0})`} testID="ext-comm-input" keyboardType="numeric" value={comm} onChangeText={setComm} /></View>
      </View>
      <Text style={s.label}>Status pembayaran</Text>
      <View style={{ marginHorizontal: -sp.lg }}>
        <Chips testPrefix="ext-status" value={status} onChange={setStatus} options={[{ label: "Belum cair", value: "pending" }, { label: "Sudah cair", value: "settled" }]} />
      </View>
      <View style={{ gap: 2, marginVertical: sp.md }}>
        <View style={[s.row, { justifyContent: "space-between" }]}><Text style={s.sub}>Total pesanan</Text><Text style={s.title}>{rp(gross)}</Text></View>
        <View style={[s.row, { justifyContent: "space-between" }]}><Text style={s.sub}>Komisi {commPct}%</Text><Text style={s.title}>-{rp(commission)}</Text></View>
        <View style={[s.row, { justifyContent: "space-between" }]}><Text style={s.sub}>Estimasi diterima outlet</Text><Text style={[s.value, { color: colors.brandPrimary }]}>{rp(net)}</Text></View>
      </View>
      <Btn title="Simpan Pesanan" testID="ext-submit-button" loading={busy} disabled={!lines.length} onPress={submit} />
    </Sheet>
  );
}
