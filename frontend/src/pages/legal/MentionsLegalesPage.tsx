import { LegalLayout } from "./LegalLayout";

export function MentionsLegalesPage() {
  return (
    <LegalLayout eyebrow="Légal" title="Mentions légales" majLe="26 septembre 2026">
      <h2>Éditeur du site</h2>
      <p>
        À ce stade (phase pilote, avant portage institutionnel), LuluSchools est édité par :<br />
        <strong>Gracio Topanou</strong> — porteur du projet<br />
        Contact : <a href="mailto:contact@luluschools.bj">contact@luluschools.bj</a><br />
        Site personnel : <a href="https://www.graciotopanou.online/" target="_blank" rel="noopener noreferrer">graciotopanou.online</a>
      </p>
      <div className="legal-note">
        LuluSchools est architecturé pour un mandat ministériel officiel (République du Bénin) : le rôle
        « Admin ministériel » de la plateforme est conçu pour être occupé par le ministère en charge de
        l'Éducation dès l'adoption institutionnelle. Tant que ce portage n'est pas formalisé, la responsabilité
        éditoriale reste celle du porteur du projet ci-dessus, conformément à l'article 328 de la loi n° 2017-20
        portant Code du numérique (obligation générale d'information).
      </div>

      <h2>Hébergement</h2>
      <p>
        Backend et base de données : Render (Render Services Inc.) — <a href="https://render.com" target="_blank" rel="noopener noreferrer">render.com</a><br />
        Frontend : Vercel Inc. — <a href="https://vercel.com" target="_blank" rel="noopener noreferrer">vercel.com</a> (ou Netlify en secours)
      </p>

      <h2>Prestataires techniques tiers</h2>
      <ul>
        <li><strong>Kkiapay</strong> — agrégateur de paiement mobile money/carte (République du Bénin), pour toutes les transactions payantes de la plateforme.</li>
        <li><strong>LuluFiles</strong> — service de stockage documentaire pour les pièces jointes (candidatures, photos, contrats).</li>
        <li><strong>FreeLLM</strong> — passerelle vers des modèles d'intelligence artificielle utilisés pour la notation de documents, la génération de quiz et l'assistant pédagogique.</li>
        <li><strong>Brevo</strong> — envoi des e-mails transactionnels (codes de vérification, identifiants).</li>
      </ul>

      <h2>Propriété intellectuelle</h2>
      <p>
        La structure générale, les textes, marques et éléments graphiques de LuluSchools sont protégés au titre
        du droit d'auteur. Les contenus pédagogiques déposés par un enseignant ou un établissement (cours,
        devoirs, quiz) restent la propriété de leur auteur ; leur usage sur la plateforme est limité aux
        établissements et classes auxquels ils sont rattachés.
      </p>

      <h2>Signalement d'un contenu ou d'un incident</h2>
      <p>
        Conformément aux articles 497 et 500 de la loi n° 2017-20, tout contenu manifestement illicite ou toute
        atteinte à la sécurité peut être signalé à <a href="mailto:contact@luluschools.bj">contact@luluschools.bj</a>.
        Chaque module concerné (messagerie, marketplace) dispose aussi d'un bouton de signalement intégré, revu
        par l'administrateur de l'établissement concerné.
      </p>
    </LegalLayout>
  );
}
