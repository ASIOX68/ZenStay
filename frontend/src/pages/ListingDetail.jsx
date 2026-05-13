import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { Star, MapPin, BedDouble, Volume2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import DateRangePicker from "../components/DateRangePicker";
import { useAuth } from "../contexts/AuthContext";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function toISO(d) {
  if (!d) return "";
  const tz = d.getTimezoneOffset() * 60000;
  return new Date(d - tz).toISOString().slice(0, 10);
}
function diffDays(a, b) {
  if (!a || !b) return 0;
  return Math.max(0, Math.round((b - a) / 86400000));
}

export default function ListingDetail() {
  const { id } = useParams();
  const { user, login } = useAuth();
  const { lang, t } = useLang();
  const [l, setL] = useState(null);
  const [range, setRange] = useState();
  const [voyageurs, setVoyageurs] = useState(2);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(null);
  const [paying, setPaying] = useState(false);

  useEffect(() => {
    axios.get(`${API}/listings/${id}`).then((r) => setL(r.data));
  }, [id]);

  useEffect(() => {
    if (user) {
      setName((n) => n || user.name || "");
      setEmail((e) => e || user.email || "");
    }
  }, [user]);

  const nights = useMemo(() => diffDays(range?.from, range?.to) || 1, [range]);
  const total = useMemo(() => (l ? (l.prix_nuit * nights).toFixed(2) : "0.00"), [l, nights]);

  if (!l) {
    return (
      <div>
        <Navbar />
        <main className="max-w-5xl mx-auto px-6 py-20">Loading…</main>
        <Footer />
      </div>
    );
  }

  const title = lang === "en" && l.titre_en ? l.titre_en : l.titre;
  const desc = lang === "en" && l.description_en ? l.description_en : l.description;

  const submit = async (e) => {
    e?.preventDefault();
    if (!user) { login(); return; }
    if (!range?.from || !range?.to) { toast.error(t.booking.pick_dates); return; }
    setSubmitting(true);
    try {
      const r = await axios.post(
        `${API}/reservations`,
        {
          logement_id: l.id,
          name, email,
          date_arrivee: toISO(range.from),
          date_depart: toISO(range.to),
          voyageurs: Number(voyageurs),
        },
        { withCredentials: true }
      );
      setCreated(r.data);
      toast.success(t.booking.sent);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Erreur");
    } finally {
      setSubmitting(false);
    }
  };

  const pay = async () => {
    if (!created) return;
    setPaying(true);
    try {
      const r = await axios.post(
        `${API}/payments/checkout`,
        { reservation_id: created.id, origin_url: window.location.origin },
        { withCredentials: true }
      );
      window.location.href = r.data.url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Erreur paiement");
      setPaying(false);
    }
  };

  return (
    <div>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-10">
        <div className="rounded-3xl overflow-hidden border border-border mb-10">
          <img src={l.image_url} alt={title} className="w-full h-[60vh] object-cover" />
        </div>

        <div className="grid lg:grid-cols-3 gap-12">
          <div className="lg:col-span-2">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h1 className="font-serif text-4xl sm:text-5xl mb-3">{title}</h1>
                <p className="text-muted-foreground flex items-center gap-1.5">
                  <MapPin className="w-4 h-4" /> {l.ville}, {l.pays}
                </p>
              </div>
              <div className="text-right">
                <div className="flex items-center justify-end gap-1 text-sm">
                  <Star className="w-4 h-4 fill-current" /> {l.note?.toFixed(2)}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 my-6">
              <Pill icon={<Volume2 className="w-3.5 h-3.5" />} label={`< ${l.db_nuit} dB`} highlight />
              <Pill icon={<BedDouble className="w-3.5 h-3.5" />} label={`${l.prix_nuit}€ / ${t.listings.per_night.replace("/ ", "")}`} />
            </div>

            <p className="text-base leading-relaxed text-muted-foreground max-w-2xl" data-testid="listing-description">
              {desc}
            </p>
          </div>

          <aside className="lg:sticky lg:top-24 self-start rounded-2xl border border-border bg-card p-7" data-testid="booking-card">
            {created ? (
              <ConfirmedBlock created={created} total={total} pay={pay} paying={paying} t={t} />
            ) : (
              <form onSubmit={submit} className="space-y-4">
                <h2 className="font-serif text-2xl mb-2">{t.booking.title}</h2>
                <Field label={t.booking.dates}>
                  <DateRangePicker range={range} onChange={setRange} testid="booking-date-range" />
                </Field>
                <Field label={t.booking.travelers}>
                  <Input type="number" min="1" max="20" value={voyageurs} onChange={(e) => setVoyageurs(e.target.value)} data-testid="booking-travelers" />
                </Field>
                <Field label={t.booking.name}>
                  <Input value={name} onChange={(e) => setName(e.target.value)} required data-testid="booking-name" />
                </Field>
                <Field label={t.booking.email}>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="booking-email" />
                </Field>

                <div className="flex items-center justify-between text-sm pt-2 border-t border-border">
                  <span className="text-muted-foreground">{nights} {t.booking.nights}</span>
                  <span className="font-medium text-lg" data-testid="booking-total">{total}€</span>
                </div>

                {!user ? (
                  <Button type="button" onClick={login} className="w-full h-12 rounded-xl" data-testid="booking-login-cta">
                    {t.booking.submit_login}
                  </Button>
                ) : (
                  <Button type="submit" disabled={submitting} className="w-full h-12 rounded-xl" data-testid="booking-submit">
                    {submitting ? "…" : t.booking.submit}
                  </Button>
                )}
              </form>
            )}
          </aside>
        </div>
      </main>
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

function Pill({ icon, label, highlight }) {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs ${highlight ? "" : "border border-border"}`}
      style={highlight ? { background: "rgba(233, 245, 237, 0.95)", color: "#2C523B" } : {}}
    >
      {icon} {label}
    </div>
  );
}

function ConfirmedBlock({ created, total, pay, paying, t }) {
  return (
    <div className="text-center" data-testid="booking-confirmed">
      <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-4">
        <CheckCircle2 className="w-6 h-6" />
      </div>
      <h2 className="font-serif text-2xl mb-1">{t.booking.sent}</h2>
      <p className="text-sm text-muted-foreground mb-6">{t.booking.sent_sub}</p>
      <div className="rounded-xl bg-muted p-4 text-sm mb-6 text-left space-y-1">
        <div className="flex justify-between"><span>{t.booking.arrival}</span><span>{created.date_arrivee}</span></div>
        <div className="flex justify-between"><span>{t.booking.departure}</span><span>{created.date_depart}</span></div>
        <div className="flex justify-between"><span>{t.booking.travelers}</span><span>{created.voyageurs}</span></div>
        <div className="flex justify-between font-medium pt-2 border-t border-border/60"><span>{t.booking.total}</span><span>{total}€</span></div>
      </div>
      <Button onClick={pay} disabled={paying} className="w-full h-12 rounded-xl" data-testid="pay-btn">
        {paying ? "…" : t.booking.pay}
      </Button>
    </div>
  );
}
