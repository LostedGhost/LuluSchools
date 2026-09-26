import { LegalLayout } from "./LegalLayout";

export function PolitiqueConfidentialitePage() {
  return (
    <LegalLayout eyebrow="Légal" title="Politique de confidentialité" majLe="26 septembre 2026">
      <p>
        Cette politique explique quelles données personnelles LuluSchools traite, pourquoi, combien de temps, et
        les droits dont vous disposez — conformément au Livre V de la loi béninoise n° 2017-20 portant Code du
        numérique (protection des données à caractère personnel).
      </p>

      <h2>1. Responsable du traitement</h2>
      <p>
        Le responsable du traitement est l'éditeur identifié dans les <a href="/mentions-legales">mentions légales</a>.
        Un délégué à la protection des données sera désigné conformément à l'article 430 dès le portage
        institutionnel de la plateforme (le traitement étant alors effectué par un organisme public).
      </p>

      <h2>2. Données que nous traitons, et pourquoi</h2>
      <ul>
        <li><strong>Identité et contact</strong> (nom, prénom, e-mail, matricule, date de naissance) — créer et sécuriser votre compte, générer le matricule officiel de l'élève.</li>
        <li><strong>Lien de filiation</strong> (tuteur ↔ enfant) — permettre l'inscription et le suivi scolaire par le tuteur légal.</li>
        <li><strong>Documents de candidature et casier judiciaire</strong> (enseignants) — évaluer une candidature à un poste ; le casier judiciaire est chiffré, stocké à part et jamais transmis au pipeline de notation automatique (Art. 395).</li>
        <li><strong>Contenu pédagogique et résultats</strong> (cours, devoirs, notes, bulletins) — assurer le suivi scolaire.</li>
        <li><strong>Messages, signalements</strong> — permettre la communication interne ; toute conversation impliquant un élève est conservée de façon inaltérable à des fins de preuve et de protection des mineurs (Art. 519, 521, 550).</li>
        <li><strong>Transactions et paiements</strong> (tickets, actes, micro-jobs, marketplace) — exécuter le service payé ; les identifiants de transaction Kkiapay sont conservés, jamais les moyens de paiement eux-mêmes.</li>
        <li><strong>Journaux techniques</strong> (connexion, erreurs) — sécurité et bon fonctionnement du service.</li>
      </ul>

      <h2>3. Décisions assistées par intelligence artificielle</h2>
      <p>
        Certaines évaluations (notation d'un document de candidature, correction d'un devoir, génération d'un
        quiz) sont assistées par un modèle d'IA. Conformément à l'article 401, aucune de ces décisions n'est
        automatisée à 100 % sans recours possible : un score en échec ou contesté est toujours réexaminé
        manuellement par un enseignant ou un administrateur.
      </p>

      <h2>4. Mineurs</h2>
      <p>
        En dessous de 16 ans, le traitement des données d'un élève n'est licite qu'avec le consentement explicite
        et horodaté de son tuteur légal (Art. 446). Au-delà de 16 ans, l'élève peut valider lui-même son
        inscription. L'accès à certains modules (marketplace, micro-jobs rémunérés) reste réservé aux élèves de
        16 ans ou plus, indépendamment de ce consentement.
      </p>

      <h2>5. Durée de conservation</h2>
      <ul>
        <li>Compte et données de scolarité : durée de la scolarité, puis archivage académique.</li>
        <li>Contrat enseignant signé électroniquement : 10 ans (Art. 346).</li>
        <li>Casier judiciaire : seul un statut vérifié (conforme / non conforme) est conservé durablement ; le contenu brut est chiffré et purgé selon la politique de rétention en vigueur.</li>
        <li>Messages impliquant un élève : conservés sans purge automatique, pour rester disponibles en cas de signalement ou de recours.</li>
      </ul>

      <h2>6. Destinataires et sous-traitants</h2>
      <p>
        Vos données ne sont jamais vendues. Elles sont partagées uniquement avec les prestataires techniques
        listés dans les mentions légales (hébergement, stockage documentaire, IA, paiement, e-mail
        transactionnel), chacun agissant sur instruction du responsable du traitement.
      </p>

      <h2>7. Transferts hors du Bénin</h2>
      <p>
        Certains prestataires (hébergement cloud, IA) traitent des données en dehors du territoire béninois.
        Conformément aux articles 391 et 392, ce transfert repose sur votre consentement, donné lors de la
        création de votre compte, et sur des mesures de sécurité contractuelles avec chaque prestataire.
      </p>

      <h2>8. Sécurité</h2>
      <p>
        Mots de passe chiffrés (Argon2), casier judiciaire chiffré (Fernet), communications en HTTPS, accès
        cloisonné par rôle et par établissement (Art. 425, 426). Toute violation de données affectant vos
        informations vous serait notifiée sans délai, ainsi qu'à l'Autorité de Protection des Données
        Personnelles (APDP), conformément à l'article 427.
      </p>

      <h2>9. Vos droits</h2>
      <p>Vous pouvez, gratuitement (Art. 421), à tout moment :</p>
      <ul>
        <li>accéder à vos données et savoir comment elles sont traitées (Art. 437) ;</li>
        <li>en demander la portabilité (Art. 438) ;</li>
        <li>vous opposer à un traitement pour motif légitime (Art. 440) ;</li>
        <li>demander la rectification ou la suppression de données inexactes (Art. 441) ;</li>
        <li>retirer un consentement précédemment donné, sans effet rétroactif ;</li>
        <li>introduire une réclamation auprès de l'Autorité de Protection des Données Personnelles (APDP) si vous estimez vos droits non respectés (Art. 448).</li>
      </ul>
      <p>Pour exercer ces droits, écrivez à <a href="mailto:contact@luluschools.bj">contact@luluschools.bj</a>.</p>
    </LegalLayout>
  );
}
