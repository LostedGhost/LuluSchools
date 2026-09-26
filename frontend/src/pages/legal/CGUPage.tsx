import { LegalLayout } from "./LegalLayout";

export function CGUPage() {
  return (
    <LegalLayout eyebrow="Légal" title="Conditions générales d'utilisation" majLe="26 septembre 2026">
      <p>
        L'utilisation de LuluSchools implique l'acceptation pleine et entière des présentes conditions,
        conformément à l'article 328 de la loi n° 2017-20 (obligation générale d'information des utilisateurs
        d'un service en ligne).
      </p>

      <h2>1. Accès et comptes</h2>
      <p>
        L'accès est réservé aux personnes rattachées à un établissement inscrit sur la plateforme : tuteur,
        élève, enseignant, administrateur d'établissement ou administrateur ministériel. Un compte élève ou
        enseignant provisionné reçoit un mot de passe temporaire à changer dès la première connexion. Chaque
        utilisateur est responsable de la confidentialité de ses identifiants.
      </p>

      <h2>2. Comportement attendu</h2>
      <p>
        Chaque utilisateur s'engage à fournir des informations exactes, à ne pas usurper l'identité d'autrui, et
        à signaler tout contenu ou comportement inapproprié via les outils de signalement intégrés (messagerie,
        annonces de la marketplace). Toute conversation impliquant un élève est journalisée de façon
        inaltérable, conformément à la protection renforcée des mineurs (articles 519, 521 et 550).
      </p>

      <h2>3. Contenus pédagogiques</h2>
      <p>
        Les cours, devoirs et quiz publiés par un enseignant restent sa propriété intellectuelle. Leur diffusion
        sur la plateforme est limitée aux élèves des classes auxquelles ils sont rattachés.
      </p>

      <h2>4. Services payants</h2>
      <p>
        Les actes académiques, tickets de transport/cantine, billets d'événements et micro-jobs sont payés via
        Kkiapay (mobile money/carte). Un prix affiché inclut toutes les taxes applicables, conformément à
        l'article 328. Le contrat est formé à la confirmation du paiement ; sa conservation est assurée pendant
        10 ans lorsque la loi l'exige (Art. 346).
      </p>

      <h2>5. Marketplace étudiante — conditions particulières</h2>
      <p>
        La marketplace est réservée aux élèves de 16 ans ou plus, au sein de leur propre établissement. C'est un
        espace d'échange <strong>entre particuliers</strong> : le vendeur n'agit pas comme professionnel, ce qui
        place ces transactions hors du régime consumériste du Livre IV (droit de rétractation, garanties légales
        — Art. 326 alinéa 4). LuluSchools sécurise néanmoins le paiement par séquestre : la somme n'est versée au
        vendeur qu'après confirmation de la remise par l'acheteur, avec un délai de 5 jours pour contester une
        réception non conforme. En cas de litige, l'administrateur de l'établissement arbitre et motive sa
        décision. Sont strictement interdits : armes, alcool, tabac, produits pharmaceutiques ou stupéfiants,
        contenus à caractère sexuel, contrefaçons.
      </p>

      <h2>6. Micro-jobs entre pairs</h2>
      <p>
        Les micro-jobs suivent le même principe de séquestre. Publier une demande et payer est ouvert à tous les
        rôles authentifiés ; accepter une mission rémunérée (être payé) est réservé aux rôles majeurs par
        construction (enseignant, tuteur, administrateur), l'âge minimum légal de rémunération d'un mineur étant
        une question de droit du travail hors du périmètre du présent Code numérique.
      </p>

      <h2>7. Décisions assistées par IA</h2>
      <p>
        Certaines évaluations utilisent l'intelligence artificielle (notation de documents, correction de
        devoirs). Aucune de ces décisions n'est appliquée sans possibilité de recours humain, conformément à
        l'article 401.
      </p>

      <h2>8. Modération et sanctions</h2>
      <p>
        L'administrateur d'un établissement peut retirer un contenu ou une annonce non conforme, avec motif
        conservé, y compris de sa propre initiative. Un manquement grave et répété aux présentes conditions peut
        entraîner la suspension du compte concerné.
      </p>

      <h2>9. Responsabilité</h2>
      <p>
        Conformément à l'article 329, LuluSchools répond de la bonne exécution des services qu'elle fournit
        directement, mais ne peut être tenue responsable du contenu déposé par un utilisateur ou du non-respect,
        par un vendeur ou un prestataire, des engagements pris envers un autre utilisateur.
      </p>

      <h2>10. Droit applicable</h2>
      <p>
        Les présentes conditions sont soumises au droit béninois. Tout litige relève des juridictions
        compétentes de la République du Bénin.
      </p>

      <h2>11. Modification</h2>
      <p>
        Ces conditions peuvent évoluer avec la plateforme. La date de dernière mise à jour figure en haut de
        cette page ; toute modification substantielle sera annoncée aux utilisateurs.
      </p>
    </LegalLayout>
  );
}
