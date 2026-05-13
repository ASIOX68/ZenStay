import React from "react";
import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { Button } from "../components/ui/button";
import { useLang } from "../contexts/LanguageContext";

export default function HostPage() {
  const { t } = useLang();
  return (
    <div>
      <Navbar />
      <main className="max-w-3xl mx-auto px-6 py-24 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-primary mb-3">ZenStay Hosts</p>
        <h1 className="font-serif text-5xl mb-6">{t.cta.become_host}</h1>
        <p className="text-muted-foreground mb-8">{t.cta.become_host_sub}</p>
        <Button asChild className="rounded-full h-12 px-8">
          <Link to="/">{t.payment.back}</Link>
        </Button>
      </main>
      <Footer />
    </div>
  );
}
