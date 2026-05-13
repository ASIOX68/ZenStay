import React from "react";
import { useLang } from "../contexts/LanguageContext";

export default function Footer() {
  const { t } = useLang();
  return (
    <footer className="border-t border-border mt-24 bg-muted/30">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-14 grid md:grid-cols-3 gap-10">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-primary" />
            <span className="font-serif text-2xl">ZenStay</span>
          </div>
          <p className="text-sm text-muted-foreground max-w-xs">{t.footer.tag}</p>
        </div>
        <div className="text-sm">
          <p className="text-xs uppercase tracking-[0.25em] text-primary mb-3">Navigation</p>
          <ul className="space-y-2 text-muted-foreground">
            <li><a href="/listings" className="hover:text-foreground">{t.nav.listings}</a></li>
            <li><a href="/host" className="hover:text-foreground">{t.nav.become_host}</a></li>
          </ul>
        </div>
        <div className="text-sm">
          <p className="text-xs uppercase tracking-[0.25em] text-primary mb-3">Légal</p>
          <ul className="space-y-2 text-muted-foreground">
            <li>CGU</li>
            <li>Confidentialité</li>
            <li>{t.footer.made}</li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
