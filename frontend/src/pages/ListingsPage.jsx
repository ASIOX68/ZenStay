import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { SlidersHorizontal, X } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ListingCard from "../components/ListingCard";
import { Button } from "../components/ui/button";
import { Slider } from "../components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ListingsPage() {
  const { t } = useLang();
  const [listings, setListings] = useState([]);
  const [country, setCountry] = useState("all");
  const [maxDb, setMaxDb] = useState([35]);
  const [priceRange, setPriceRange] = useState([0, 500]);

  useEffect(() => {
    axios.get(`${API}/listings`).then((r) => {
      const data = r.data || [];
      setListings(data);
      const prices = data.map((d) => d.prix_nuit);
      if (prices.length) setPriceRange([Math.floor(Math.min(...prices) / 10) * 10, Math.ceil(Math.max(...prices) / 10) * 10]);
    });
  }, []);

  const countries = useMemo(() => Array.from(new Set(listings.map((l) => l.pays).filter(Boolean))), [listings]);

  const filtered = listings.filter(
    (l) =>
      (country === "all" || l.pays === country) &&
      l.db_nuit <= maxDb[0] &&
      l.prix_nuit >= priceRange[0] &&
      l.prix_nuit <= priceRange[1]
  );

  const reset = () => {
    setCountry("all");
    setMaxDb([35]);
    const prices = listings.map((d) => d.prix_nuit);
    if (prices.length) setPriceRange([Math.floor(Math.min(...prices) / 10) * 10, Math.ceil(Math.max(...prices) / 10) * 10]);
  };

  return (
    <div>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 lg:px-10 py-14">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-2">{t.listings.title}</p>
        <h1 className="font-serif text-4xl sm:text-5xl mb-10">{t.listings.subtitle}</h1>

        <div className="grid lg:grid-cols-[280px_1fr] gap-10">
          {/* Filters sidebar */}
          <aside className="lg:sticky lg:top-24 self-start rounded-2xl border border-border bg-card p-6 space-y-7 h-fit" data-testid="filters-panel">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-primary" />
                <h2 className="font-serif text-xl">{t.filters.title}</h2>
              </div>
              <Button variant="ghost" size="sm" onClick={reset} data-testid="filters-reset" className="text-xs">
                <X className="w-3.5 h-3.5 mr-1" /> {t.filters.reset}
              </Button>
            </div>

            <FilterBlock label={t.filters.country}>
              <Select value={country} onValueChange={setCountry}>
                <SelectTrigger className="h-11" data-testid="filter-country">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t.filters.all_countries}</SelectItem>
                  {countries.map((c) => (
                    <SelectItem key={c} value={c} data-testid={`filter-country-${c}`}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FilterBlock>

            <FilterBlock label={`${t.filters.price_range} · ${priceRange[0]}€ – ${priceRange[1]}€`}>
              <Slider
                value={priceRange}
                onValueChange={setPriceRange}
                min={0}
                max={500}
                step={10}
                data-testid="filter-price"
                className="mt-3"
              />
            </FilterBlock>

            <FilterBlock label={`${t.filters.max_db} · < ${maxDb[0]} dB`}>
              <Slider
                value={maxDb}
                onValueChange={setMaxDb}
                min={20}
                max={35}
                step={1}
                data-testid="filter-db"
                className="mt-3"
              />
            </FilterBlock>

            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground pt-2 border-t border-border" data-testid="filter-results-count">
              {filtered.length} {t.filters.results}
            </p>
          </aside>

          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-7">
            {filtered.map((l, i) => (
              <ListingCard key={l.id} l={l} index={i} />
            ))}
            {filtered.length === 0 && (
              <p className="text-muted-foreground">—</p>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function FilterBlock({ label, children }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.25em] text-primary mb-2">{label}</p>
      {children}
    </div>
  );
}
