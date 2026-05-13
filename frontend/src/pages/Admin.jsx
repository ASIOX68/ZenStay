import React, { useEffect, useState } from "react";
import axios from "axios";
import { Navigate } from "react-router-dom";
import { Pencil, Trash2, Plus, ToggleLeft, ToggleRight } from "lucide-react";
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

const EMPTY = {
  titre: "", titre_en: "", ville: "", pays: "France",
  prix_nuit: 150, note: 4.8, db_nuit: 28,
  image_url: "", description: "", description_en: "",
  hote_email: "", disponible: true,
};

export default function Admin() {
  const { user, loading } = useAuth();
  const { t } = useLang();
  const [tab, setTab] = useState("listings");
  const [listings, setListings] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [editing, setEditing] = useState(null);
  const [open, setOpen] = useState(false);

  const fetchAll = async () => {
    const [a, b] = await Promise.all([
      axios.get(`${API}/admin/listings`, { withCredentials: true }),
      axios.get(`${API}/admin/reservations`, { withCredentials: true }),
    ]);
    setListings(a.data); setBookings(b.data);
  };

  useEffect(() => { if (user?.role === "admin") fetchAll().catch(() => {}); }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;

  const save = async () => {
    try {
      const payload = { ...editing, prix_nuit: Number(editing.prix_nuit), note: Number(editing.note), db_nuit: Number(editing.db_nuit) };
      if (editing.id) {
        await axios.put(`${API}/admin/listings/${editing.id}`, payload, { withCredentials: true });
      } else {
        await axios.post(`${API}/admin/listings`, payload, { withCredentials: true });
      }
      toast.success("OK"); setOpen(false); fetchAll();
    } catch (e) { toast.error(e?.response?.data?.detail || "Erreur"); }
  };

  const remove = async (id) => {
    if (!window.confirm("Supprimer ?")) return;
    await axios.delete(`${API}/admin/listings/${id}`, { withCredentials: true });
    fetchAll();
  };

  const toggle = async (id) => {
    await axios.patch(`${API}/admin/listings/${id}/toggle`, {}, { withCredentials: true });
    fetchAll();
  };

  return (
    <div>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-12">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-2">Admin</p>
        <h1 className="font-serif text-4xl sm:text-5xl mb-8">{t.admin.title}</h1>

        <div className="flex gap-2 mb-6">
          {["listings", "bookings"].map((k) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`px-5 h-10 rounded-full border transition-colors ${tab === k ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-muted"}`}
              data-testid={`admin-tab-${k}`}
            >
              {k === "listings" ? t.admin.listings : t.admin.bookings}
            </button>
          ))}
        </div>

        {tab === "listings" && (
          <div>
            <div className="flex justify-end mb-4">
              <Button onClick={() => { setEditing({ ...EMPTY }); setOpen(true); }} data-testid="admin-new-listing">
                <Plus className="w-4 h-4 mr-1" /> {t.admin.new}
              </Button>
            </div>
            <div className="rounded-2xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/60 text-left">
                  <tr>
                    <th className="p-3">Titre</th><th className="p-3">Ville</th><th className="p-3">Prix</th><th className="p-3">dB</th><th className="p-3">Hôte</th><th className="p-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {listings.map((l) => (
                    <tr key={l.id} className="border-t border-border" data-testid={`admin-listing-row-${l.id}`}>
                      <td className="p-3">{l.titre}</td>
                      <td className="p-3">{l.ville}</td>
                      <td className="p-3">{l.prix_nuit}€</td>
                      <td className="p-3">{l.db_nuit}</td>
                      <td className="p-3 text-muted-foreground text-xs">{l.hote_email}</td>
                      <td className="p-3 flex gap-2 justify-end">
                        <Button size="sm" variant="ghost" onClick={() => toggle(l.id)} data-testid={`toggle-${l.id}`}>
                          {l.disponible ? <ToggleRight className="w-4 h-4 text-primary" /> : <ToggleLeft className="w-4 h-4" />}
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => { setEditing(l); setOpen(true); }} data-testid={`edit-${l.id}`}>
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => remove(l.id)} data-testid={`delete-${l.id}`}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === "bookings" && (
          <div className="rounded-2xl border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-left">
                <tr>
                  <th className="p-3">Client</th><th className="p-3">Email</th><th className="p-3">Dates</th><th className="p-3">Pax</th><th className="p-3">Montant</th><th className="p-3">Statut</th>
                </tr>
              </thead>
              <tbody>
                {bookings.map((b) => (
                  <tr key={b.id} className="border-t border-border" data-testid={`booking-row-${b.id}`}>
                    <td className="p-3">{b.name}</td>
                    <td className="p-3">{b.email}</td>
                    <td className="p-3">{b.date_arrivee} → {b.date_depart}</td>
                    <td className="p-3">{b.voyageurs}</td>
                    <td className="p-3">{b.montant}€</td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded-full text-xs ${b.statut === "paid" ? "bg-primary/10 text-primary" : "bg-muted"}`}>{b.statut}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editing?.id ? t.admin.edit : t.admin.new}</DialogTitle>
          </DialogHeader>
          {editing && (
            <div className="grid sm:grid-cols-2 gap-3 max-h-[60vh] overflow-y-auto pr-1">
              <Field label="Titre (FR)"><Input value={editing.titre} onChange={(e) => setEditing({ ...editing, titre: e.target.value })} data-testid="form-titre" /></Field>
              <Field label="Titre (EN)"><Input value={editing.titre_en || ""} onChange={(e) => setEditing({ ...editing, titre_en: e.target.value })} /></Field>
              <Field label="Ville"><Input value={editing.ville} onChange={(e) => setEditing({ ...editing, ville: e.target.value })} /></Field>
              <Field label="Pays"><Input value={editing.pays || ""} onChange={(e) => setEditing({ ...editing, pays: e.target.value })} /></Field>
              <Field label="Prix / nuit (€)"><Input type="number" value={editing.prix_nuit} onChange={(e) => setEditing({ ...editing, prix_nuit: e.target.value })} /></Field>
              <Field label="dB nuit"><Input type="number" value={editing.db_nuit} onChange={(e) => setEditing({ ...editing, db_nuit: e.target.value })} /></Field>
              <Field label="Note"><Input type="number" step="0.1" value={editing.note} onChange={(e) => setEditing({ ...editing, note: e.target.value })} /></Field>
              <Field label="Hôte email"><Input value={editing.hote_email} onChange={(e) => setEditing({ ...editing, hote_email: e.target.value })} /></Field>
              <div className="sm:col-span-2">
                <Field label="Image">
                  <ImageUpload value={editing.image_url} onChange={(url) => setEditing({ ...editing, image_url: url })} />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Description (FR)"><Textarea value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Description (EN)"><Textarea value={editing.description_en || ""} onChange={(e) => setEditing({ ...editing, description_en: e.target.value })} /></Field>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t.admin.cancel}</Button>
            <Button onClick={save} data-testid="form-save">{t.admin.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Footer />
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
