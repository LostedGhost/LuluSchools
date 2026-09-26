import { LegalLayout } from "./LegalLayout";

export function PolitiqueCookiesPage() {
  return (
    <LegalLayout eyebrow="Légal" title="Politique de cookies" majLe="26 septembre 2026">
      <p>
        LuluSchools utilise très peu de traceurs, et aucun à des fins publicitaires. Voici, en toute
        transparence, ce que la plateforme stocke réellement dans votre navigateur.
      </p>

      <h2>1. Stockage strictement nécessaire</h2>
      <p>
        Votre session (jeton de connexion et jeton de rafraîchissement) est conservée dans le stockage local de
        votre navigateur (<code>localStorage</code>), pas dans un cookie classique. Elle sert uniquement à vous
        garder connecté et n'est jamais transmise à un tiers. Elle est supprimée à la déconnexion ou en vidant
        les données de site de votre navigateur.
      </p>
      <p>
        Une préférence d'affichage (thème clair/sombre) est également conservée localement, pour votre confort
        de lecture d'une visite à l'autre.
      </p>

      <h2>2. Aucun cookie publicitaire ou de mesure d'audience</h2>
      <p>
        LuluSchools n'installe aucun cookie publicitaire, de traçage inter-sites ou de mesure d'audience
        (Google Analytics ou équivalent). Aucune donnée de navigation n'est revendue ou partagée à des fins
        marketing.
      </p>

      <h2>3. Widget de paiement Kkiapay</h2>
      <p>
        Lors d'un paiement, un module fourni par Kkiapay (notre prestataire de paiement mobile money/carte) est
        chargé depuis leurs serveurs. Ce module peut déposer ses propres cookies techniques, nécessaires au bon
        déroulement du paiement, sous la responsabilité de Kkiapay et selon sa propre politique.
      </p>

      <h2>4. Vos choix</h2>
      <p>
        Vous pouvez à tout moment vider le stockage local de votre navigateur ; cela vous déconnectera de
        LuluSchools mais n'affecte aucun autre site. Comme le stockage utilisé est strictement nécessaire au
        fonctionnement du service, aucun bandeau de consentement n'est requis pour celui-ci.
      </p>
    </LegalLayout>
  );
}
