import React, { useEffect, useState } from "react";
import axios from "axios";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { useAuth } from "../contexts/AuthContext";
import { useLang } from "../contexts/LanguageContext";
import { Link, Navigate } from "react-router-dom";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Dashboard() {
  const { user, loading } = useAuth();
  const { t } = useLang();
  const [bookings, setBookings] = useState([]);

  useEffect(() => {
    if (user) axios.get(`${API}/reservations/me`, { withCredentials: true }).then((r) => setBookings(r.data));
  }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/" replace />;

  return (
    <div>
      <Navbar />
      <main className="max-w-5xl mx-auto px-6 lg:px-10 py-14">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-2">ZenStay</p>
        <h1 className="font-serif text-4xl sm:text-5xl mb-10">{t.nav.my_bookings}</h1>
        <div className="space-y-4">
          {bookings.length === 0 && (
            <p className="text-muted-foreground">— <Link to="/listings" className="underline">{t.listings.view}</Link></p>
          )}
          {bookings.map((b) => (
            <div key={b.id} className="rounded-2xl border border-border bg-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4" data-testid={`booking-${b.id}`}>
              <div>
                <p className="text-sm text-muted-foreground">{b.date_arrivee} → {b.date_depart} · {b.voyageurs} pax</p>
                <p className="font-serif text-2xl mt-1">{b.montant}€</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1.5 rounded-full text-xs uppercase tracking-widest ${b.statut === "paid" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>
                  {b.statut}
                </span>
                {b.statut !== "paid" && b.stripe_link && (
                  <a href={b.stripe_link} className="text-sm underline">{t.booking.pay}</a>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}
