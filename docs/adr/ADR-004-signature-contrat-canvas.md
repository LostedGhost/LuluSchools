# ADR-004 : Signature du contrat enseignant par tracé manuel (canvas)

## Statut
Accepté (clôt le point ouvert laissé par UC-05 : aucun prestataire de signature électronique qualifiée n'a été identifié).

## Contexte
UC-05 prévoyait initialement une signature électronique qualifiée dès la V1 (Art. 287 de la loi n° 2017-20 — dispositif certifié, prestataire de confiance agréé). Aucun prestataire n'a été choisi et le sujet est resté un point ouvert pendant toute l'implémentation du backend. L'utilisateur a tranché : la signature se fait par un tracé dessiné au doigt ou au stylet sur une zone (`div`/canvas) côté client, exporté en image.

## Décision
`POST /contrats/{id}/signer` accepte un fichier image (`multipart/form-data`, champ `signature_image`) plutôt qu'un texte. Le backend stocke cette image via LuluFiles (`signature_image_lulufiles_id`), horodate la signature et calcule un hash SHA-256 du texte du contrat au moment de la signature (`signature_hash_document`) pour la piste d'audit.

Base légale : Art. 284-285 de la loi n° 2017-20 — une signature électronique simple est admise dans les transactions électroniques ; elle n'a pas la présomption de fiabilité forte d'une signature qualifiée (Art. 285, dispositif certifié), mais elle est valable. Un tracé manuel capturé et lié à l'acte, avec horodatage et hash du document, constitue une signature électronique simple recevable.

## Alternatives considérées
- **Signature électronique qualifiée** (décision initiale) : abandonnée faute de prestataire identifié à ce jour. Reste possible en évolution future si un prestataire est retenu — le champ `signature_image_lulufiles_id` n'empêche pas d'ajouter plus tard un certificat qualifié en complément.
- **Nom tapé + case à cocher** (implémentation transitoire précédente) : remplacée, moins conforme à l'intention de l'utilisateur (une vraie signature manuscrite numérisée) et pas plus solide juridiquement qu'un tracé réel.

## Conséquences
Facilite : expérience utilisateur proche d'une signature papier, aucune dépendance à un prestataire tiers, coût nul.
Rend plus coûteux/risqué : valeur probante plus faible qu'une signature qualifiée en cas de contestation judiciaire ; l'authenticité du tracé (venant bien du titulaire du compte) repose sur l'authentification JWT au moment de l'upload, pas sur une preuve biométrique du tracé lui-même — acceptable pour la Phase 1, à réévaluer si le volume de litiges le justifie.
