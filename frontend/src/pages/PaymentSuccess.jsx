import React, { useEffect, useRef, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { Button } from "../components/ui/button";
import { useLang } from "../contexts/LanguageContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const { t } = useLang();
  const [state, setState] = useState({ phase: "checking" });
  const attempts = useRef(0);

  useEffect(() => {
    if (!sessionId) {
      setState({ phase: "failed" });
      return;
    }
    let timer = null;
    const poll = async () => {
      attempts.current += 1;
      try {
        const r = await axios.get(`${API}/payments/status/${sessionId}`);
        if (r.data.payment_status === "paid") {
          setState({ phase: "paid", data: r.data });
          return;
        }
        if (r.data.status === "expired" || attempts.current >= 8) {
          setState({ phase: "failed", data: r.data });
          return;
        }
        timer = setTimeout(poll, 2000);
      } catch (e) {
        if (attempts.current >= 8) setState({ phase: "failed" });
        else timer = setTimeout(poll, 2000);
      }
    };
    poll();
    return () => timer && clearTimeout(timer);
  }, [sessionId]);

  return (
    <div>
      <Navbar />
      <main className="max-w-2xl mx-auto px-6 py-24 text-center">
        {state.phase === "checking" && (
          <div data-testid="payment-checking">
            <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin mb-6" />
            <h1 className="font-serif text-3xl mb-2">{t.payment.checking}</h1>
          </div>
        )}
        {state.phase === "paid" && (
          <div data-testid="payment-paid">
            <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h1 className="font-serif text-4xl sm:text-5xl mb-3">{t.payment.success}</h1>
            <p className="text-muted-foreground mb-8">{t.payment.success_sub}</p>
            <Button asChild className="rounded-full h-12 px-8" data-testid="back-home">
              <Link to="/">{t.payment.back}</Link>
            </Button>
          </div>
        )}
        {state.phase === "failed" && (
          <div data-testid="payment-failed">
            <div className="w-16 h-16 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-8 h-8" />
            </div>
            <h1 className="font-serif text-3xl mb-3">{t.payment.failed}</h1>
            <Button asChild variant="outline" className="rounded-full h-12 px-8">
              <Link to="/">{t.payment.back}</Link>
            </Button>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
