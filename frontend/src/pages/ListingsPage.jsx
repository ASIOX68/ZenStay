import React, { useEffect, useState } from "react";
import axios from "axios";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ListingCard from "../components/ListingCard";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ListingsPage() {
  const { t } = useLang();
  const [listings, setListings] = useState([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    axios.get(`${API}/listings`).then((r) => setListings(r.data || []));
  }, []);

  const filtered = listings.filter(
    (l) =>
      !q ||
      l.ville?.toLowerCase().includes(q.toLowerCase()) ||
      l.titre?.toLowerCase().includes(q.toLowerCase()) ||
      l.pays?.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-14">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-2">{t.listings.title}</p>
        <h1 className="font-serif text-4xl sm:text-5xl mb-8">{t.listings.subtitle}</h1>

        <div className="mb-10 max-w-md">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t.hero.location}
            className="w-full h-12 rounded-xl border border-border bg-card px-4 outline-none focus:border-primary transition-colors"
            data-testid="listings-search-input"
          />
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-7">
          {filtered.map((l, i) => (
            <ListingCard key={l.id} l={l} index={i} />
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}
