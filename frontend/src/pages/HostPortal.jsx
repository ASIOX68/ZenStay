import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import axios from "axios";
import { Pencil, ToggleLeft, ToggleRight, Wallet, BedDouble, BarChart3 } from "lucide-react";
import { toast } from "sonner";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import ImageUpload from "../components/ImageUpload";
import { useAuth } from "../contexts/AuthContext";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function fmtEUR(v) {
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(Number(v) || 0);
}

export default function HostPortal() {
  const { user, loading } = useAuth();
  const { t } = useLang();
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("listings");
  const [listings, setListings] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [stats, setStats] = useState(null);
  const [editing, setEditing] = useState(null);
  const [open, setOpen] = useState(false);

  const refresh = async () => {
    try {
      const [a, b, c, m] = await Promise.all([
        axios.get(`${API}/host/listings`, { withCredentials: true }),
        axios.get(`${API}/host/reservations`, { withCredentials: true }),
        axios.get(`${API}/host/stats`, { withCredentials: true }),
        axios.get(`${API}/host/me`, { withCredentials: true }),
      ]);
      setListings(a.data); setReservations(b.data); setStats(c.data); setMe(m.data);
    } catch (e) {
      // not auth — useEffect navigate
    }
  };

  useEffect(() => { if (user) refresh(); }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/" replace />;
  if (me && !me.is_host) return <Navigate to="/" replace />;

  const save = async () => {
    try {
      const payload = {
        titre: editing.titre,
        titre_en: editing.titre_en || "",
        ville: editing.ville,
        pays: editing.pays || "France",
        prix_nuit: Number(editing.prix_nuit),
        note: Number(editing.note),
        db_nuit: Number(editing.db_nuit),
        image_url: editing.image_url,
        description: editing.description,
        description_en: editing.description_en || "",
        hote_email: editing.hote_email,
        disponible: editing.disponible,
      };
      await axios.put(`${API}/host/listings/${editing.id}`, payload, { withCredentials: true });
      toast.success("OK"); setOpen(false); refresh();
    } catch (e) { toast.error(e?.response?.data?.detail || "Erreur"); }
  };

  const toggle = async (id) => {
    await axios.patch(`${API}/host/listings/${id}/toggle`, {}, { withCredentials: true });
    refresh();
  };

  return (
    <div>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-12">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-2" data-testid="host-portal-eyebrow">{t.host_portal.eyebrow}</p>
        <h1 className="font-serif text-4xl sm:text-5xl mb-8">{t.host_portal.title}</h1>

        {/* Stats cards */}
        {stats && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10" data-testid="host-stats">
            <StatCard icon={<Wallet className="w-4 h-4" />} label={t.host_portal.revenue_paid} value={fmtEUR(stats.revenue_paid_eur)} highlight testid="stat-revenue-paid" />
            <StatCard icon={<Wallet className="w-4 h-4" />} label={t.host_portal.revenue_pending} value={fmtEUR(stats.revenue_pending_eur)} testid="stat-revenue-pending" />
            <StatCard icon={<BedDouble className="w-4 h-4" />} label={t.host_portal.total_bookings} value={stats.reservations_total} testid="stat-bookings-total" />
            <StatCard icon={<BarChart3 className="w-4 h-4" />} label={`${t.host_portal.paid_bookings} / ${t.host_portal.pending_bookings}`} value={`${stats.reservations_paid} / ${stats.reservations_pending}`} testid="stat-bookings-split" />
          </div>
        )}

        <div className="flex gap-2 mb-6">
          {[
            { k: "listings", l: t.host_portal.tabs.listings },
            { k: "reservations", l: t.host_portal.tabs.reservations },
            { k: "revenue", l: t.host_portal.tabs.revenue },
          ].map(({ k, l }) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`px-5 h-10 rounded-full border transition-colors ${tab === k ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-muted"}`}
              data-testid={`host-tab-${k}`}
            >
              {l}
            </button>
          ))}
        </div>

        {tab === "listings" && (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
            {listings.length === 0 && <p className="text-muted-foreground">{t.host_portal.empty_listings}</p>}
            {listings.map((l) => (
              <div key={l.id} className="rounded-2xl border border-border bg-card overflow-hidden" data-testid={`host-listing-${l.id}`}>
                <div className="relative aspect-[4/3] bg-muted overflow-hidden">
                  <img src={l.image_url} alt={l.titre} className="w-full h-full object-cover" />
                  <span className="absolute top-3 left-3 px-3 py-1.5 rounded-full text-xs font-semibold" style={{ background: "rgba(233,245,237,0.95)", color: "#2C523B" }}>
                    &lt; {l.db_nuit} dB
                  </span>
                  <span className={`absolute top-3 right-3 px-3 py-1.5 rounded-full text-xs ${l.disponible ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
                    {l.disponible ? t.host_portal.available : t.host_portal.unavailable}
                  </span>
                </div>
                <div className="p-5">
                  <h3 className="font-serif text-xl">{l.titre}</h3>
                  <p className="text-sm text-muted-foreground mb-3">{l.ville}, {l.pays}</p>
                  <div className="flex items-end justify-between">
                    <p><span className="text-2xl font-medium">{Math.round(l.prix_nuit)}€</span><span className="text-xs text-muted-foreground ml-1">/ nuit</span></p>
                    <div className="flex gap-2">
                      <Button size="sm" variant="ghost" onClick={() => toggle(l.id)} data-testid={`host-toggle-${l.id}`}>
                        {l.disponible ? <ToggleRight className="w-4 h-4 text-primary" /> : <ToggleLeft className="w-4 h-4" />}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => { setEditing(l); setOpen(true); }} className="rounded-full" data-testid={`host-edit-${l.id}`}>
                        <Pencil className="w-3.5 h-3.5 mr-1" /> {t.host_portal.edit}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "reservations" && (
          <div className="rounded-2xl border border-border overflow-hidden bg-card">
            {reservations.length === 0 ? (
              <p className="p-6 text-muted-foreground">{t.host_portal.empty_reservations}</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-muted/60 text-left">
                  <tr>
                    <th className="p-3">Hébergement</th>
                    <th className="p-3">Voyageur</th>
                    <th className="p-3">Dates</th>
                    <th className="p-3">Pax</th>
                    <th className="p-3">Montant</th>
                    <th className="p-3">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {reservations.map((r) => (
                    <tr key={r.id} className="border-t border-border" data-testid={`host-res-${r.id}`}>
                      <td className="p-3">{r.listing_titre}</td>
                      <td className="p-3">
                        <div>{r.name}</div>
                        <div className="text-xs text-muted-foreground">{r.email}</div>
                      </td>
                      <td className="p-3">{r.date_arrivee} → {r.date_depart}</td>
                      <td className="p-3">{r.voyageurs}</td>
                      <td className="p-3">{fmtEUR(r.montant)}</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-full text-xs ${r.statut === "paid" ? "bg-primary/10 text-primary" : "bg-muted"}`}>
                          {r.statut}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {tab === "revenue" && stats && (
          <div className="grid md:grid-cols-2 gap-6 max-w-3xl">
            <RevenueBig label={t.host_portal.revenue_paid} value={fmtEUR(stats.revenue_paid_eur)} sub={`${stats.reservations_paid} ${t.host_portal.paid_bookings.toLowerCase()}`} highlight />
            <RevenueBig label={t.host_portal.revenue_pending} value={fmtEUR(stats.revenue_pending_eur)} sub={`${stats.reservations_pending} ${t.host_portal.pending_bookings.toLowerCase()}`} />
          </div>
        )}
      </main>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{t.host_portal.edit}</DialogTitle></DialogHeader>
          {editing && (
            <div className="grid sm:grid-cols-2 gap-3 max-h-[60vh] overflow-y-auto pr-1">
              <Field label="Titre (FR)"><Input value={editing.titre} onChange={(e) => setEditing({ ...editing, titre: e.target.value })} /></Field>
              <Field label="Titre (EN)"><Input value={editing.titre_en || ""} onChange={(e) => setEditing({ ...editing, titre_en: e.target.value })} /></Field>
              <Field label="Ville"><Input value={editing.ville} onChange={(e) => setEditing({ ...editing, ville: e.target.value })} /></Field>
              <Field label="Pays"><Input value={editing.pays || ""} onChange={(e) => setEditing({ ...editing, pays: e.target.value })} /></Field>
              <Field label="Prix / nuit (€)"><Input type="number" value={editing.prix_nuit} onChange={(e) => setEditing({ ...editing, prix_nuit: e.target.value })} /></Field>
              <Field label="dB nuit"><Input type="number" value={editing.db_nuit} onChange={(e) => setEditing({ ...editing, db_nuit: e.target.value })} /></Field>
              <div className="sm:col-span-2">
                <Field label="Image"><ImageUpload value={editing.image_url} onChange={(url) => setEditing({ ...editing, image_url: url })} /></Field>
              </div>
              <div className="sm:col-span-2"><Field label="Description (FR)"><Textarea value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></Field></div>
              <div className="sm:col-span-2"><Field label="Description (EN)"><Textarea value={editing.description_en || ""} onChange={(e) => setEditing({ ...editing, description_en: e.target.value })} /></Field></div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t.host_portal.cancel}</Button>
            <Button onClick={save} data-testid="host-save">{t.host_portal.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Footer />
    </div>
  );
}

function StatCard({ icon, label, value, highlight, testid }) {
  return (
    <div className={`rounded-2xl border border-border p-5 ${highlight ? "bg-primary/5" : "bg-card"}`} data-testid={testid}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-primary mb-3">
        {icon} {label}
      </div>
      <p className="font-serif text-3xl">{value}</p>
    </div>
  );
}

function RevenueBig({ label, value, sub, highlight }) {
  return (
    <div className={`rounded-3xl p-10 border border-border ${highlight ? "bg-primary text-primary-foreground" : "bg-card"}`}>
      <p className={`text-xs uppercase tracking-[0.25em] mb-3 ${highlight ? "opacity-80" : "text-primary"}`}>{label}</p>
      <p className="font-serif text-5xl">{value}</p>
      <p className={`text-sm mt-2 ${highlight ? "opacity-80" : "text-muted-foreground"}`}>{sub}</p>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <Label className="text-[10px] uppercase tracking-[0.25em] text-primary mb-1.5 block">{label}</Label>
      {children}
    </div>
  );
}
