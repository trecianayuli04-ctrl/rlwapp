import { useState } from "react";
import { FlatList, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { api, num, rp, useApi } from "@/src/api";
import { Btn, Card, Chips, Field, Header, Page, Sheet, sp, Stat, StateView, useStyles, useToast } from "@/src/ui";
import { useTheme } from "@/src/theme";

const CATS = {
  income: ["Penjualan", "Lainnya"],
  expense: ["Gaji", "Sewa", "Listrik", "Air", "WiFi", "Purchasing", "Marketing", "Operasional"],
};

export default function Finance() {
  const s = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { data, loading, error, reload } = useApi<any[]>("/finance");
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<"income" | "expense">("expense");
  const [cat, setCat] = useState("Operasional");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const inc = (data || []).filter((f) => f.type === "income").reduce((a, f) => a + f.amount, 0);
  const exp = (data || []).filter((f) => f.type === "expense").reduce((a, f) => a + f.amount, 0);

  const submit = async () => {
    setBusy(true);
    try {
      await api("/finance", { body: { type, category: cat, amount: num(amount), note } });
      toast("Transaksi keuangan dicatat");
      setOpen(false);
      setAmount("");
      setNote("");
      reload();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <Header back title="Keuangan" subtitle="Bulan ini · penjualan, purchasing & gaji tercatat otomatis" right={<Btn small title="Catat" icon="add" testID="finance-add-button" onPress={() => setOpen(true)} />} />
      {!data ? <StateView loading={loading} error={error} onRetry={reload} /> : (
        <FlatList
          data={data}
          keyExtractor={(f) => f.id}
          contentContainerStyle={[s.list, { paddingBottom: insets.bottom + sp.xl }]}
          ListHeaderComponent={
            <View style={s.wrap}>
              <Stat label="Pemasukan" value={rp(inc)} tone="success" testID="finance-income" />
              <Stat label="Pengeluaran" value={rp(exp)} tone="error" testID="finance-expense" />
              <Stat label="Cash Flow" value={rp(inc - exp)} tone={inc - exp >= 0 ? "success" : "error"} testID="finance-net" />
            </View>
          }
          ListEmptyComponent={<StateView empty="Belum ada transaksi" />}
          renderItem={({ item: f }) => (
            <Card style={[s.row, { justifyContent: "space-between" }]}>
              <View style={{ flex: 1 }}>
                <Text style={s.title}>{f.category}</Text>
                <Text style={s.sub} numberOfLines={1}>{f.note} · {f.date}</Text>
              </View>
              <Text style={[s.value, { color: f.type === "income" ? colors.success : colors.error }]}>{f.type === "income" ? "+" : "-"}{rp(f.amount)}</Text>
            </Card>
          )}
        />
      )}
      <Sheet visible={open} onClose={() => setOpen(false)} title="Catat Keuangan" testID="finance-sheet">
        <View style={{ marginHorizontal: -sp.lg }}>
          <Chips testPrefix="finance-type" value={type} onChange={(v) => { setType(v); setCat(CATS[v][0]); }} options={[{ label: "Pengeluaran", value: "expense" }, { label: "Pemasukan", value: "income" }]} />
          <Chips testPrefix="finance-cat" value={cat} onChange={setCat} options={CATS[type].map((c) => ({ label: c, value: c }))} />
        </View>
        <Field label="Jumlah (Rp)" testID="finance-amount-input" keyboardType="numeric" value={amount} onChangeText={setAmount} />
        <Field label="Keterangan" testID="finance-note-input" value={note} onChangeText={setNote} />
        <Btn title="Simpan" testID="finance-submit-button" loading={busy} disabled={!num(amount)} onPress={submit} />
      </Sheet>
    </Page>
  );
}
