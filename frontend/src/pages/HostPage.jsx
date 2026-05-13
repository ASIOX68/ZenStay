import React, { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, ArrowRight, Volume2, Mountain, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function HostPage() {
  const { t } = useLang();
  const [form, setForm] = useState({ name: "", email: "", phone: "", location: "", db_estimate: 30, description: "" });
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${API}/host-contact`, {
        ...form,
        db_estimate: Number(form.db_estimate) || null,
      });
      setSent(true);
      toast.success(t.host.sent);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Erreur");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 lg:px-10 py-16">
        <div className="grid lg:grid-cols-2 gap-14 items-start">
          {/* Left: copy */}
          <div className="lg:sticky lg:top-24">
            <p className="text-xs uppercase tracking-[0.3em] text-primary mb-3" data-testid="host-eyebrow">
              {t.host.eyebrow}
            </p>
            <h1 className="font-serif text-5xl sm:text-6xl leading-[1.05] mb-6">
              {t.host.title.split("\n").map((line, i) => <span key={i} className="block">{line}</span>)}
            </h1>
            <p className="text-muted-foreground leading-relaxed mb-10 max-w-md">{t.host.subtitle}</p>

            <div className="space-y-4">
              <Feature icon={<Volume2 className="w-4 h-4" />} text="Sonomètre vérifié sur 7 nuits" textEn="Sound meter verified over 7 nights" />
              <Feature icon={<Mountain className="w-4 h-4" />} text="Visibilité confidentielle" textEn="Discreet visibility" />
              <Feature icon={<ShieldCheck className="w-4 h-4" />} text="Validation manuelle, sans algorithme" textEn="Manual validation, no algorithm" />
            </div>
          </div>

          {/* Right: form */}
          <div className="rounded-3xl border border-border bg-card p-8 md:p-10">
            {sent ? (
              <div className="text-center py-10" data-testid="host-form-sent">
                <div className="w-14 h-14 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-5">
                  <CheckCircle2 className="w-7 h-7" />
                </div>
                <h2 className="font-serif text-3xl mb-3">{t.host.sent}</h2>
                <p className="text-muted-foreground mb-8">{t.host.sent_sub}</p>
                <Button asChild className="rounded-full h-12 px-8" data-testid="host-back-home">
                  <Link to="/">{t.payment.back} <ArrowRight className="ml-2 w-4 h-4" /></Link>
                </Button>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-5" data-testid="host-form">
                <div className="grid sm:grid-cols-2 gap-4">
                  <FieldLabel label={t.host.name}>
                    <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="host-name" className="h-12" />
                  </FieldLabel>
                  <FieldLabel label={t.host.email}>
                    <Input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="host-email" className="h-12" />
                  </FieldLabel>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <FieldLabel label={t.host.phone}>
                    <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="host-phone" className="h-12" />
                  </FieldLabel>
                  <FieldLabel label={t.host.db_estimate}>
                    <Input type="number" min="15" max="60" value={form.db_estimate} onChange={(e) => setForm({ ...form, db_estimate: e.target.value })} data-testid="host-db" className="h-12" />
                  </FieldLabel>
                </div>
                <FieldLabel label={t.host.location}>
                  <Input required value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="host-location" className="h-12" />
                </FieldLabel>
                <FieldLabel label={t.host.description}>
                  <Textarea required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="host-description" className="min-h-[140px]" />
                </FieldLabel>
                <Button type="submit" disabled={submitting} className="w-full h-12 rounded-xl" data-testid="host-submit">
                  {submitting ? "…" : t.host.submit}
                </Button>
              </form>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function FieldLabel({ label, children }) {
  return (
    <div>
      <Label className="text-[10px] uppercase tracking-[0.25em] text-primary mb-1.5 block">{label}</Label>
      {children}
    </div>
  );
}

function Feature({ icon, text, textEn }) {
  const { lang } = useLang();
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center">{icon}</span>
      <span>{lang === "en" ? textEn : text}</span>
    </div>
  );
}
