import { useState } from "react";
import { FlatList, Image, Pressable, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, num, rp, useApi } from "@/src/api";
import { useAuth } from "@/src/auth";
import { Badge, Btn, Card, Chips, Field, Header, Icon, Page, Sheet, sp, Stat, StateView, useStyles, useToast } from "@/src/ui";
import { useTheme } from "@/src/theme";

export default function Finance() {
  const s = useStyles();
  const { colors } = useTheme();
  const { can } = useAuth();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { data, loading, error, reload } = useApi<any[]>("/finance");
  const { data: cats } = useApi<any[]>("/config/expense_categories?active=true");
  const { data: pockets } = useApi<any[]>("/config/fund_pockets?active=true");
  const { data: methods } = useApi<any[]>("/config/payment_methods?active=true");
  const { data: pending, reload: reloadPending } = useApi<any[]>(can("petty_cash_approve") ? "/expenses?pending=true" : null);
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<"income" | "expense">("expense");
  const [cat, setCat] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [method, setMethod] = useState("Cash");
  const [receiver, setReceiver] = useState("");
  const [photo, setPhoto] = useState("");
  const [viewPhoto, setViewPhoto] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inc = (data || []).filter((f) => f.type === "income").reduce((a, f) => a + f.amount, 0);
  const exp = (data || []).filter((f) => f.type === "expense").reduce((a, f) => a + f.amount, 0);
  const expenseCats = (cats || []).map((c) => c.name);
  const incomeCats = ["Penjualan", "Lainnya"];
  const list = type === "expense" ? expenseCats : incomeCats;

  const pick = async (camera: boolean) => {
    const perm = camera ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return toast("Izin kamera/galeri ditolak", "error");
    const res = camera
      ? await ImagePicker.launchCameraAsync({ base64: true, quality: 0.5, mediaTypes: ["images"] })
      : await ImagePicker.launchImageLibraryAsync({ base64: true, quality: 0.5, mediaTypes: ["images"] });
    if (!res.canceled && res.assets?.[0]?.base64) setPhoto(`data:image/jpeg;base64,${res.assets[0].base64}`);
  };

  const openSheet = () => {
    setType("expense");
    setCat(expenseCats[0] || "");
    setAmount("");
    setNote("");
    setMethod("Cash");
    setReceiver("");
    setPhoto("");
    setOpen(true);
  };
  const submit = async () => {
    setBusy(true);
    try {
      if (type === "expense") {
        const pocket = (cats || []).find((c) => c.name === cat)?.pocket_id || null;
        await api("/expenses", { body: { category: cat, amount: num(amount), note, method, pocket_id: pocket, receiver, photo, source: "finance" } });
      } else {
        await api("/finance", { body: { type, category: cat, amount: num(amount), note } });
      }
      toast("Tersimpan");
      setOpen(false);
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };
  const decide = async (id: string, approve: boolean) => {
    try {
      await api(`/expenses/${id}/decide`, { body: { approve } });
      toast(approve ? "Disetujui & masuk pengeluaran" : "Ditolak");
      reloadPending();
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    }
  };

  return (
    <Page>
      <Header back title="Keuangan" subtitle="Pencatatan pengeluaran & pemasukan" right={<Btn small title="Catat" icon="add" testID="finance-add-button" onPress={openSheet} />} />
      {!data ? <StateView loading={loading} error={error} onRetry={reload} /> : (
        <FlatList
          data={data}
          keyExtractor={(f) => f.id}
          contentContainerStyle={[s.list, { paddingBottom: insets.bottom + sp.xl }]}
          ListHeaderComponent={
            <View style={{ gap: sp.md }}>
              <View style={s.wrap}>
                <Stat label="Pemasukan" value={rp(inc)} tone="success" testID="finance-income" />
                <Stat label="Pengeluaran" value={rp(exp)} tone="error" testID="finance-expense" />
                <Stat label="Cash Flow" value={rp(inc - exp)} tone={inc - exp >= 0 ? "success" : "error"} testID="finance-net" />
              </View>
              {!!(pending || []).length && (
                <>
                  <Text style={s.section}>Menunggu Persetujuan</Text>
                  {pending!.map((p) => (
                    <Card key={p.id} testID={`pending-${p.id}`}>
                      <View style={[s.row, { justifyContent: "space-between" }]}>
                        <Text style={[s.title, { flex: 1 }]}>{p.category} · {rp(p.amount)}</Text>
                        <Badge label="PENDING" tone="warning" />
                      </View>
                      <Text style={s.sub}>{p.note} · {p.user_name} · {p.method}</Text>
                      {!!p.photo && <Pressable onPress={() => setViewPhoto(p.photo)}><Text style={[s.sub, { color: colors.brandPrimary }]}>Lihat bukti foto</Text></Pressable>}
                      <View style={[s.row, { marginTop: sp.sm }]}>
                        <Btn small title="Tolak" variant="ghost" style={{ flex: 1 }} testID={`reject-${p.id}`} onPress={() => decide(p.id, false)} />
                        <Btn small title="Setujui" variant="success" style={{ flex: 1 }} testID={`approve-${p.id}`} onPress={() => decide(p.id, true)} />
                      </View>
                    </Card>
                  ))}
                </>
              )}
              <Text style={s.section}>Transaksi Bulan Ini</Text>
            </View>
          }
          ListEmptyComponent={<StateView empty="Belum ada transaksi" />}
          renderItem={({ item: f }) => (
            <Card style={[s.row, { justifyContent: "space-between" }]} onPress={f.photo ? () => setViewPhoto(f.photo) : undefined}>
              <View style={{ flex: 1 }}>
                <Text style={s.title}>{f.category}{f.source === "platform" ? " · App" : ""}</Text>
                <Text style={s.sub} numberOfLines={1}>{f.note} · {f.date}{f.method ? ` · ${f.method}` : ""}</Text>
                {!!f.photo && <Text style={[s.sub, { color: colors.brandPrimary }]}>Ada bukti foto</Text>}
              </View>
              <Text style={[s.value, { color: f.type === "income" ? colors.success : colors.error }]}>{f.type === "income" ? "+" : "-"}{rp(f.amount)}</Text>
            </Card>
          )}
        />
      )}
      <Sheet visible={open} onClose={() => setOpen(false)} title="Catat Keuangan" testID="finance-sheet">
        <View style={{ marginHorizontal: -sp.lg }}>
          <Chips testPrefix="finance-type" value={type} onChange={(v) => { setType(v); setCat((v === "expense" ? expenseCats : incomeCats)[0] || ""); }} options={[{ label: "Pengeluaran", value: "expense" }, { label: "Pemasukan", value: "income" }]} />
          <Chips testPrefix="finance-cat" value={cat} onChange={setCat} options={list.map((c) => ({ label: c, value: c }))} />
        </View>
        <Field label="Jumlah (Rp)" testID="finance-amount-input" keyboardType="numeric" value={amount} onChangeText={setAmount} />
        <Field label="Keterangan" testID="finance-note-input" value={note} onChangeText={setNote} />
        {type === "expense" && (
          <>
            <Text style={s.label}>Metode / sumber dana</Text>
            <View style={{ marginHorizontal: -sp.lg }}>
              <Chips testPrefix="finance-method" value={method} onChange={setMethod} options={(methods || []).map((m) => ({ label: m.name, value: m.name }))} />
            </View>
            <Field label="Penerima / vendor (opsional)" testID="finance-receiver-input" value={receiver} onChangeText={setReceiver} />
            <View style={[s.row, { marginBottom: sp.md }]}>
              <Btn title="Kamera" variant="secondary" icon="camera-outline" style={{ flex: 1 }} testID="finance-camera-button" onPress={() => pick(true)} />
              <Btn title="Galeri" variant="secondary" icon="image-outline" style={{ flex: 1 }} testID="finance-gallery-button" onPress={() => pick(false)} />
            </View>
            {!!photo && <Image source={{ uri: photo }} style={{ width: "100%", height: 160, borderRadius: 12, marginBottom: sp.md }} resizeMode="cover" />}
          </>
        )}
        <Btn title="Simpan" testID="finance-submit-button" loading={busy} disabled={!num(amount) || !cat} onPress={submit} />
      </Sheet>
      <Sheet visible={!!viewPhoto} onClose={() => setViewPhoto(null)} title="Bukti Foto" testID="photo-view">
        {!!viewPhoto && <Image source={{ uri: viewPhoto }} style={{ width: "100%", height: 360, borderRadius: 12 }} resizeMode="contain" />}
        <Btn title="Tutup" variant="ghost" icon="close" style={{ marginTop: sp.md }} onPress={() => setViewPhoto(null)} />
      </Sheet>
    </Page>
  );
}
