import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { LanguageProvider } from "./contexts/LanguageContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";

import Landing from "./pages/Landing";
import ListingsPage from "./pages/ListingsPage";
import ListingDetail from "./pages/ListingDetail";
import PaymentSuccess from "./pages/PaymentSuccess";
import Dashboard from "./pages/Dashboard";
import Admin from "./pages/Admin";
import HostPage from "./pages/HostPage";
import HostPortal from "./pages/HostPortal";
import InvoicePage from "./pages/InvoicePage";
import AuthCallback from "./components/AuthCallback";

function AppRouter() {
  const location = useLocation();
  // CRITICAL: Check URL fragment for session_id synchronously during render
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/listings" element={<ListingsPage />} />
      <Route path="/listings/:id" element={<ListingDetail />} />
      <Route path="/payment-success" element={<PaymentSuccess />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/host" element={<HostPage />} />
      <Route path="/host-portal" element={<HostPortal />} />
      <Route path="/invoices/:invoice_number" element={<InvoicePage />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <LanguageProvider>
          <BrowserRouter>
            <AuthProvider>
              <AppRouter />
              <Toaster position="top-center" richColors />
            </AuthProvider>
          </BrowserRouter>
        </LanguageProvider>
      </ThemeProvider>
    </div>
  );
}
