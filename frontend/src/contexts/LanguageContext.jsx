import React, { createContext, useContext, useState, useCallback } from "react";

const dict = {
  fr: {
    nav: { listings: "Séjours", become_host: "Devenir hôte", admin: "Admin", login: "Se connecter", logout: "Se déconnecter", my_bookings: "Mes réservations" },
    hero: {
      eyebrow: "Séjours < 35 dB",
      title: "Dormir dans le silence,\nse réveiller dans la nature.",
      subtitle: "Une sélection rare d'habitats au son mesuré, choisis pour la qualité de leur nuit — pas de route, pas de bruit, juste le souffle du vent.",
      location: "Où ?", dates: "Quand ?", travelers: "Voyageurs",
      search: "Rechercher",
    },
    listings: {
      title: "Six refuges, six silences",
      subtitle: "Tous mesurés sous les 35 décibels la nuit.",
      per_night: "/ nuit",
      view: "Découvrir",
      unavailable: "Indisponible",
      noise: "< 35 dB la nuit",
    },
    why: {
      eyebrow: "Pourquoi ZenStay",
      title: "Le silence est un luxe rare.\nOn l'a mesuré pour vous.",
      cards: [
        { t: "Sonomètre vérifié", d: "Chaque hébergement est mesuré sur 7 nuits consécutives avant validation." },
        { t: "Loin de tout", d: "Aucune route à moins de 800m. Pas de voisin direct." },
        { t: "Nature certifiée", d: "Forêts, montagnes, îles, falaises — pas de centres urbains." },
        { t: "Hôtes confidentiels", d: "Coordonnées privées, contact à votre arrivée." },
      ],
    },
    cta: { become_host: "Proposer mon refuge", become_host_sub: "Vous possédez un lieu calme, isolé ? Listez-le en 3 minutes." },
    booking: {
      title: "Réserver ce séjour",
      arrival: "Date d'arrivée",
      departure: "Date de départ",
      travelers: "Voyageurs",
      name: "Nom complet",
      email: "Email",
      total: "Total",
      nights: "nuits",
      submit_login: "Se connecter pour réserver",
      submit: "Réserver",
      sent: "Réservation envoyée",
      pay: "Payer mon séjour",
      sent_sub: "Confirmez votre séjour en procédant au paiement.",
    },
    payment: {
      success: "Paiement reçu — séjour confirmé",
      success_sub: "Vous recevrez les coordonnées de l'hôte par email.",
      back: "Retour à l'accueil",
      checking: "Vérification du paiement…",
      failed: "Le paiement a échoué ou expiré.",
    },
    admin: {
      title: "Tableau de bord — Admin",
      listings: "Hébergements",
      bookings: "Réservations",
      new: "Nouveau",
      edit: "Modifier", delete: "Supprimer", toggle: "Disponibilité",
      save: "Enregistrer", cancel: "Annuler",
    },
    footer: { tag: "Séjours mesurés sous 35 dB. Repos garanti.", made: "© ZenStay 2026" },
    auth: { signing_in: "Connexion en cours…" },
  },
  en: {
    nav: { listings: "Stays", become_host: "Become a host", admin: "Admin", login: "Sign in", logout: "Sign out", my_bookings: "My bookings" },
    hero: {
      eyebrow: "Stays < 35 dB",
      title: "Sleep in silence,\nwake up in nature.",
      subtitle: "A rare selection of habitats with measured sound — chosen for the quality of their night. No road, no noise, only the breath of wind.",
      location: "Where?", dates: "When?", travelers: "Travelers",
      search: "Search",
    },
    listings: {
      title: "Six refuges, six silences",
      subtitle: "All measured below 35 decibels at night.",
      per_night: "/ night",
      view: "Discover",
      unavailable: "Unavailable",
      noise: "< 35 dB at night",
    },
    why: {
      eyebrow: "Why ZenStay",
      title: "Silence is a rare luxury.\nWe measure it for you.",
      cards: [
        { t: "Verified sound meter", d: "Every stay is measured over 7 consecutive nights before listing." },
        { t: "Far from everything", d: "No road within 800m. No direct neighbors." },
        { t: "Certified nature", d: "Forests, mountains, islands, cliffs — never urban centers." },
        { t: "Discreet hosts", d: "Host details private, given on arrival." },
      ],
    },
    cta: { become_host: "List my refuge", become_host_sub: "You own a calm, isolated place? List it in 3 minutes." },
    booking: {
      title: "Book this stay",
      arrival: "Arrival date",
      departure: "Departure date",
      travelers: "Travelers",
      name: "Full name",
      email: "Email",
      total: "Total",
      nights: "nights",
      submit_login: "Sign in to book",
      submit: "Book",
      sent: "Reservation sent",
      pay: "Pay my stay",
      sent_sub: "Confirm your stay by completing payment.",
    },
    payment: {
      success: "Payment received — stay confirmed",
      success_sub: "You'll receive the host's details by email.",
      back: "Back to home",
      checking: "Checking payment…",
      failed: "Payment failed or expired.",
    },
    admin: {
      title: "Dashboard — Admin",
      listings: "Listings",
      bookings: "Bookings",
      new: "New",
      edit: "Edit", delete: "Delete", toggle: "Availability",
      save: "Save", cancel: "Cancel",
    },
    footer: { tag: "Stays measured below 35 dB. Rest guaranteed.", made: "© ZenStay 2026" },
    auth: { signing_in: "Signing in…" },
  },
};

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("zen_lang") || "fr");
  const setL = useCallback((l) => {
    setLang(l);
    localStorage.setItem("zen_lang", l);
  }, []);
  const t = dict[lang];
  return (
    <LanguageContext.Provider value={{ lang, setLang: setL, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLang() {
  return useContext(LanguageContext);
}
