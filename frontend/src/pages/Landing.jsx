import React, { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, Mountain, Trees, Waves } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import ListingCard from "../components/ListingCard";
import { Button } from "../components/ui/button";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const HERO_BG = "https://static.prod-images.emergentagent.com/jobs/cbdace80-319e-4c8e-9618-57c3eff20477/images/91fffc191b72dafcd7c9567731c42c0b70859aa9efc85c6b5955c47601b7849f.png";

export default function Landing() {
  const { t } = useLang();
  const [listings, setListings] = useState([]);

  useEffect(() => {
    axios.get(`${API}/listings`).then((r) => setListings(r.data || [])).catch(() => {});
  }, []);

  return (
    <div className="App relative">
      <Navbar />

      {/* HERO */}
      <section className="relative overflow-hidden">
        <img src={HERO_BG} alt="" className="absolute inset-0 w-full h-full object-cover opacity-90" />
        <div className="absolute inset-0 bg-background/30 dark:bg-background/60" />
        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 pt-20 pb-32 lg:pt-32 lg:pb-44">
          <span
            className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-primary mb-6"
            data-testid="hero-eyebrow"
          >
            <span className="pulse-dot" /> {t.hero.eyebrow}
          </span>
          <h1
            className="font-serif text-5xl sm:text-6xl lg:text-7xl leading-[1.05] tracking-tight max-w-3xl"
            data-testid="hero-title"
          >
            {t.hero.title.split("\n").map((line, i) => (
              <span key={i} className="block">{line}</span>
            ))}
          </h1>
          <p className="mt-6 text-base sm:text-lg text-muted-foreground max-w-xl leading-relaxed">
            {t.hero.subtitle}
          </p>

          {/* SEARCH */}
          <div className="mt-10 max-w-3xl rounded-2xl bg-card/95 backdrop-blur-xl border border-border shadow-xl p-2 flex flex-col md:flex-row gap-2">
            <SearchField label={t.hero.location} placeholder="Brocéliande, Folegandros…" testid="search-location" />
            <SearchField label={t.hero.dates} placeholder="—" testid="search-dates" />
            <SearchField label={t.hero.travelers} placeholder="2" testid="search-travelers" />
            <Button asChild className="rounded-xl h-14 px-8" data-testid="hero-search-btn">
              <Link to="/listings">
                {t.hero.search} <ArrowRight className="ml-1 w-4 h-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* LISTINGS GRID */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 py-20" id="listings">
        <div className="flex items-end justify-between mb-10">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-primary mb-2">{t.listings.title}</p>
            <h2 className="font-serif text-4xl sm:text-5xl leading-tight max-w-2xl">{t.listings.subtitle}</h2>
          </div>
          <Link to="/listings" className="hidden md:flex text-sm items-center gap-1 hover:text-primary transition-colors">
            {t.listings.view} <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-7" data-testid="listings-grid">
          {listings.slice(0, 6).map((l, i) => (
            <ListingCard key={l.id} l={l} index={i} />
          ))}
        </div>
      </section>

      {/* WHY ZENSTAY — bento */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 py-20">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-2">{t.why.eyebrow}</p>
        <h2 className="font-serif text-4xl sm:text-5xl leading-tight max-w-2xl mb-12">
          {t.why.title.split("\n").map((s, i) => <span key={i} className="block">{s}</span>)}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-5">
          {t.why.cards.map((c, i) => (
            <div
              key={i}
              className={`rounded-2xl border border-border bg-card p-7 md:p-9 ${i === 0 ? "md:col-span-3 md:row-span-2" : i === 1 ? "md:col-span-3" : "md:col-span-2"}`}
              data-testid={`why-card-${i}`}
            >
              <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-5">
                {i === 0 && <ShieldCheck className="w-5 h-5" />}
                {i === 1 && <Mountain className="w-5 h-5" />}
                {i === 2 && <Trees className="w-5 h-5" />}
                {i === 3 && <Waves className="w-5 h-5" />}
              </div>
              <h3 className="font-serif text-2xl mb-2">{c.t}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-md">{c.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* HOST CTA */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 py-20">
        <div className="rounded-3xl border border-border bg-primary text-primary-foreground p-10 md:p-16 flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <div className="max-w-xl">
            <p className="text-xs uppercase tracking-[0.3em] mb-3 opacity-80">ZenStay Hosts</p>
            <h3 className="font-serif text-3xl md:text-4xl mb-3">{t.cta.become_host}</h3>
            <p className="opacity-90">{t.cta.become_host_sub}</p>
          </div>
          <Button
            asChild
            variant="secondary"
            className="rounded-full h-14 px-8"
            data-testid="become-host-cta"
          >
            <Link to="/host">
              {t.cta.become_host} <ArrowRight className="ml-2 w-4 h-4" />
            </Link>
          </Button>
        </div>
      </section>

      <Footer />
    </div>
  );
}

function SearchField({ label, placeholder, testid }) {
  return (
    <div className="flex-1 px-4 py-3 rounded-xl hover:bg-muted/60 transition-colors">
      <label className="block text-[10px] uppercase tracking-[0.25em] text-primary mb-1">{label}</label>
      <input
        className="bg-transparent w-full outline-none text-sm placeholder:text-muted-foreground"
        placeholder={placeholder}
        data-testid={testid}
      />
    </div>
  );
}
