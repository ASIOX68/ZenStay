import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { Printer, ArrowLeft, CheckCircle2, Clock } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { Button } from "../components/ui/button";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function fmtEUR(v) {
  if (typeof v !== "number") v = Number(v) || 0;
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(v);
}

export default function InvoicePage() {
  const { invoice_number } = useParams();
  const { t } = useLang();
  const [data, setData] = useState(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    axios
      .get(`${API}/invoices/${invoice_number}`)
      .then((r) => setData(r.data))
      .catch(() => setNotFound(true));
  }, [invoice_number]);

  if (notFound) {
    return (
      <div>
        <Navbar />
        <main className="max-w-2xl mx-auto px-6 py-24 text-center">
          <h1 className="font-serif text-3xl mb-4">{t.invoice.not_found}</h1>
          <Button asChild variant="outline" className="rounded-full">
            <Link to="/">{t.invoice.back}</Link>
          </Button>
        </main>
        <Footer />
      </div>
    );
  }
  if (!data) return null;

  return (
    <div>
      <div className="no-print"><Navbar /></div>
      <main className="max-w-3xl mx-auto px-6 py-10 print:py-0 print:px-0">
        <div className="no-print flex items-center justify-between mb-6">
          <Button asChild variant="ghost" size="sm" data-testid="invoice-back">
            <Link to="/"><ArrowLeft className="w-4 h-4 mr-1" /> {t.invoice.back}</Link>
          </Button>
          <Button onClick={() => window.print()} className="rounded-full" data-testid="invoice-print">
            <Printer className="w-4 h-4 mr-2" /> {t.invoice.print}
          </Button>
        </div>

        <article className="rounded-3xl border border-border bg-card p-10 print:border-0 print:rounded-none print:p-12" data-testid="invoice-doc">
          {/* Header */}
          <div className="flex items-start justify-between mb-10">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 rounded-full bg-primary" />
                <span className="font-serif text-2xl">ZenStay</span>
              </div>
              <p className="text-xs uppercase tracking-[0.25em] text-primary">{t.invoice.title}</p>
              <h1 className="font-serif text-3xl mt-1" data-testid="invoice-number">{data.invoice_number}</h1>
            </div>
            <StatusBadge statut={data.statut} t={t} />
          </div>

          {/* Bill-to */}
          <div className="grid sm:grid-cols-2 gap-6 mb-8 text-sm">
            <div>
              <p className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground mb-1.5">{t.invoice.beneficiary}</p>
              <p className="font-medium">{data.name}</p>
              <p className="text-muted-foreground">{data.email}</p>
            </div>
            <div className="sm:text-right">
              <p className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground mb-1.5">{t.invoice.issued}</p>
              <p className="font-medium">{(data.issued_at || "").slice(0, 10)}</p>
            </div>
          </div>

          {/* Stay */}
          <div className="rounded-2xl bg-muted p-6 mb-8 print:bg-transparent print:border print:border-border">
            <h2 className="font-serif text-xl mb-3">{data.listing?.titre}</h2>
            <p className="text-sm text-muted-foreground mb-4">{data.listing?.ville}, {data.listing?.pays}</p>
            <div className="grid sm:grid-cols-3 gap-4 text-sm">
              <Cell label={t.invoice.arrival} value={data.date_arrivee} />
              <Cell label={t.invoice.departure} value={data.date_depart} />
              <Cell label={t.invoice.travelers} value={data.voyageurs} />
            </div>
          </div>

          {/* Lines */}
          <table className="w-full text-sm mb-2">
            <thead className="border-b border-border">
              <tr className="text-left text-muted-foreground">
                <th className="py-3 font-normal">Description</th>
                <th className="py-3 font-normal text-right">{t.invoice.rate}</th>
                <th className="py-3 font-normal text-right">{t.invoice.subtotal}</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="py-4">
                  {data.nights} {t.invoice.nights} · {data.listing?.titre}
                </td>
                <td className="py-4 text-right">{fmtEUR(data.prix_nuit)}</td>
                <td className="py-4 text-right" data-testid="invoice-subtotal">{fmtEUR(data.subtotal)}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={2} className="py-5 text-right text-xs uppercase tracking-[0.25em] text-muted-foreground">{t.invoice.total}</td>
                <td className="py-5 text-right font-serif text-3xl" data-testid="invoice-total">{fmtEUR(data.total)}</td>
              </tr>
            </tfoot>
          </table>

          {/* Legal */}
          <div className="mt-10 pt-6 border-t border-border text-xs text-muted-foreground space-y-1">
            <p>{t.invoice.legal}</p>
            <p>{t.invoice.no_tva}</p>
            <p className="opacity-60">ZenStay — séjours mesurés sous 35 dB · contact@zenstay.com</p>
          </div>
        </article>
      </main>
      <div className="no-print"><Footer /></div>
    </div>
  );
}

function Cell({ label, value }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.25em] text-muted-foreground mb-1">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

function StatusBadge({ statut, t }) {
  const paid = statut === "paid";
  return (
    <span
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs uppercase tracking-widest ${
        paid ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
      }`}
      data-testid="invoice-status"
    >
      {paid ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
      {paid ? t.invoice.paid : t.invoice.pending}
    </span>
  );
}
