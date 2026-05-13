import React from "react";
import { Link } from "react-router-dom";
import { Star, MapPin } from "lucide-react";
import { useLang } from "../contexts/LanguageContext";

export default function ListingCard({ l, index = 0 }) {
  const { lang, t } = useLang();
  const title = lang === "en" && l.titre_en ? l.titre_en : l.titre;
  return (
    <Link
      to={`/listings/${l.id}`}
      className="listing-card group rounded-2xl overflow-hidden border border-border bg-card block fade-up"
      style={{ animationDelay: `${index * 80}ms` }}
      data-testid={`listing-card-${l.id}`}
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-muted">
        <img
          src={l.image_url}
          alt={title}
          loading="lazy"
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
        />
        <div
          className="absolute top-3 left-3 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
          style={{ background: "rgba(233, 245, 237, 0.95)", color: "#2C523B" }}
          data-testid={`noise-badge-${l.id}`}
        >
          <span className="pulse-dot" /> &lt; {l.db_nuit} dB
        </div>
        {!l.disponible && (
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center">
            <span className="text-sm font-medium uppercase tracking-widest">{t.listings.unavailable}</span>
          </div>
        )}
      </div>
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-serif text-xl leading-tight">{title}</h3>
            <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
              <MapPin className="w-3 h-3" /> {l.ville}, {l.pays}
            </p>
          </div>
          <div className="flex items-center gap-1 text-sm shrink-0">
            <Star className="w-3.5 h-3.5 fill-current" /> {l.note?.toFixed(2)}
          </div>
        </div>
        <div className="mt-4 flex items-end justify-between">
          <div>
            <span className="text-2xl font-medium">{Math.round(l.prix_nuit)}€</span>
            <span className="text-sm text-muted-foreground ml-1">{t.listings.per_night}</span>
          </div>
          <span className="text-xs uppercase tracking-[0.2em] text-primary group-hover:translate-x-1 transition-transform">
            {t.listings.view} →
          </span>
        </div>
      </div>
    </Link>
  );
}
