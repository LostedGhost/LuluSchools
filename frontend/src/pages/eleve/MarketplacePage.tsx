import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/AuthContext";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import {
  annulerTransaction,
  confirmerReception,
  contesterTransaction,
  declarerRemise,
  listerAnnonces,
  mesAnnonces,
  mesTransactions,
  obtenirAnnonce,
  publierAnnonce,
  reserverAnnonce,
  retirerMaAnnonce,
  amorcerPaiementTransaction,
  signalerAnnonce,
} from "../../api/marketplace";
import { messageErreur } from "../../api/client";
import type {
  AnnonceMarketplaceOut,
  CategorieAnnonce,
  EtatArticle,
  PhotoAnnonceLienOut,
  TransactionMarketplaceOut,
} from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  Select,
  SectionHead,
  SkeletonCard,
  SuccessBanner,
  TextArea,
  TextInput,
} from "../../components/ui";
import { KkiapayButton } from "../../components/KkiapayButton";
import { Flag, ImagePlus, ShoppingBag, Store, Trash2 } from "lucide-react";
import { estRempli } from "../../utils/validation";

const LABEL_CATEGORIE: Record<CategorieAnnonce, string> = {
  fournitures_scolaires: "Fournitures scolaires",
  manuels_livres: "Manuels & livres",
  vetements_uniformes: "Vêtements & uniformes",
  electronique: "Électronique",
  autre: "Autre",
};
const LABEL_ETAT: Record<EtatArticle, string> = {
  neuf: "Neuf",
  tres_bon_etat: "Très bon état",
  bon_etat: "Bon état",
  use: "Usé",
};
const STATUT_ANNONCE_LABEL: Record<AnnonceMarketplaceOut["statut"], string> = {
  disponible: "Disponible",
  reservee: "Réservée",
  vendue: "Vendue",
  retiree: "Retirée",
};
const STATUT_ANNONCE_TONE: Record<AnnonceMarketplaceOut["statut"], "success" | "pending" | "error" | "neutral"> = {
  disponible: "success",
  reservee: "pending",
  vendue: "neutral",
  retiree: "error",
};
const STATUT_TRANSACTION_LABEL: Record<TransactionMarketplaceOut["statut"], string> = {
  en_attente_paiement: "En attente de paiement",
  paiement_confirme: "Payée — remise à effectuer",
  remise_declaree: "Remise déclarée — en attente de confirmation",
  confirmee: "Confirmée — reversement à venir",
  contestee: "Contestée",
  finalisee: "Finalisée",
  remboursee: "Remboursée",
  annulee: "Annulée",
};
const STATUT_TRANSACTION_TONE: Record<TransactionMarketplaceOut["statut"], "pending" | "success" | "error" | "neutral" | "info"> = {
  en_attente_paiement: "pending",
  paiement_confirme: "info",
  remise_declaree: "info",
  confirmee: "info",
  contestee: "error",
  finalisee: "success",
  remboursee: "neutral",
  annulee: "neutral",
};

export function MarketplacePage() {
  const { utilisateur } = useAuth();
  const profil = useEleveProfil();
  const etablissementId = profil.etablissement_id;

  const [annonces, setAnnonces] = useState<AnnonceMarketplaceOut[]>([]);
  const [mesAnnoncesListe, setMesAnnoncesListe] = useState<AnnonceMarketplaceOut[]>([]);
  const [transactions, setTransactions] = useState<TransactionMarketplaceOut[]>([]);
  const [annonceParTransaction, setAnnonceParTransaction] = useState<Record<string, AnnonceMarketplaceOut>>({});
  const [photosParAnnonce, setPhotosParAnnonce] = useState<Record<string, PhotoAnnonceLienOut[]>>({});
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);
  const [motifContestationParId, setMotifContestationParId] = useState<Record<string, string>>({});

  const [filtreCategorie, setFiltreCategorie] = useState<CategorieAnnonce | "">("");
  const [filtreEtat, setFiltreEtat] = useState<EtatArticle | "">("");

  const [showForm, setShowForm] = useState(false);
  const [titre, setTitre] = useState("");
  const [description, setDescription] = useState("");
  const [categorie, setCategorie] = useState<CategorieAnnonce>("fournitures_scolaires");
  const [etat, setEtat] = useState<EtatArticle>("bon_etat");
  const [prix, setPrix] = useState("");
  const [photosAEnvoyer, setPhotosAEnvoyer] = useState<File[]>([]);
  const [enCoursPublication, setEnCoursPublication] = useState(false);

  const [transactionEnAttentePaiement, setTransactionEnAttentePaiement] = useState<TransactionMarketplaceOut | null>(null);

  const charger = () => {
    if (!etablissementId) {
      setChargement(false);
      return;
    }
    setChargement(true);
    Promise.all([
      listerAnnonces(etablissementId, {
        categorie: filtreCategorie || undefined,
        etat: filtreEtat || undefined,
      }),
      mesAnnonces(),
      mesTransactions(),
    ])
      .then(async ([resCatalogue, resMesAnnonces, resTransactions]) => {
        setAnnonces(resCatalogue.data.items);
        setMesAnnoncesListe(resMesAnnonces.data);
        setTransactions(resTransactions.data);

        const connues = new Map<string, AnnonceMarketplaceOut>();
        resCatalogue.data.items.forEach((a) => connues.set(a.id, a));
        resMesAnnonces.data.forEach((a) => connues.set(a.id, a));
        const idsManquants = Array.from(new Set(resTransactions.data.map((t) => t.annonce_id))).filter(
          (id) => !connues.has(id),
        );
        const annoncesManquantes = await Promise.all(idsManquants.map((id) => obtenirAnnonce(id).then((r) => r.data)));
        annoncesManquantes.forEach((a) => connues.set(a.id, a));
        setAnnonceParTransaction(Object.fromEntries(connues));
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissementId, filtreCategorie, filtreEtat]);

  const voirPhotos = async (annonceId: string) => {
    if (photosParAnnonce[annonceId]) {
      setPhotosParAnnonce((prev) => {
        const copie = { ...prev };
        delete copie[annonceId];
        return copie;
      });
      return;
    }
    try {
      const res = await obtenirAnnonce(annonceId);
      setPhotosParAnnonce((prev) => ({ ...prev, [annonceId]: res.data.photos }));
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de charger les photos de cette annonce."));
    }
  };

  const publier = async (e: FormEvent) => {
    e.preventDefault();
    if (!estRempli(titre) || !estRempli(description) || !prix || photosAEnvoyer.length === 0) {
      setErreur("Veuillez remplir tous les champs et joindre au moins une photo.");
      return;
    }
    if (!etablissementId) return;
    setErreur(null);
    setEnCoursPublication(true);
    try {
      await publierAnnonce(
        etablissementId,
        { titre: titre.trim(), description: description.trim(), categorie, etat, prix: Number(prix) },
        photosAEnvoyer,
      );
      setTitre("");
      setDescription("");
      setPrix("");
      setPhotosAEnvoyer([]);
      setShowForm(false);
      setSucces("Annonce publiée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de publier cette annonce."));
    } finally {
      setEnCoursPublication(false);
    }
  };

  const reserver = async (annonceId: string) => {
    setActionEnCoursId(annonceId);
    setErreur(null);
    try {
      const res = await reserverAnnonce(annonceId);
      setTransactionEnAttentePaiement(res.data);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de réserver cette annonce."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const payerTransaction = async (transactionId: string, transactionKkiapayId: string) => {
    setActionEnCoursId(transactionId);
    setErreur(null);
    try {
      await amorcerPaiementTransaction(transactionId, transactionKkiapayId);
      setSucces("Paiement transmis, en attente de confirmation.");
      setTransactionEnAttentePaiement(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer ce paiement."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const annulerReservation = async (transactionId: string) => {
    setActionEnCoursId(transactionId);
    setErreur(null);
    try {
      await annulerTransaction(transactionId);
      setTransactionEnAttentePaiement(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'annuler cette réservation."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const signaler = async (annonceId: string) => {
    setActionEnCoursId(annonceId);
    setErreur(null);
    try {
      await signalerAnnonce(annonceId);
      setSucces("Annonce signalée à l'administration de votre établissement.");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de signaler cette annonce."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const retirer = async (annonceId: string) => {
    setActionEnCoursId(annonceId);
    setErreur(null);
    try {
      await retirerMaAnnonce(annonceId);
      setSucces("Annonce retirée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de retirer cette annonce."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const declarer = async (transactionId: string) => {
    setActionEnCoursId(transactionId);
    setErreur(null);
    try {
      await declarerRemise(transactionId);
      setSucces("Remise déclarée. L'acheteur dispose de 5 jours pour confirmer ou contester.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de déclarer cette remise."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const confirmer = async (transactionId: string) => {
    setActionEnCoursId(transactionId);
    setErreur(null);
    try {
      await confirmerReception(transactionId);
      setSucces("Réception confirmée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const contester = async (transactionId: string) => {
    if (!motifContestationParId[transactionId]?.trim()) {
      setErreur("Veuillez détailler le motif de la contestation.");
      return;
    }
    setActionEnCoursId(transactionId);
    setErreur(null);
    try {
      await contesterTransaction(transactionId, motifContestationParId[transactionId].trim());
      setSucces("Réception contestée, l'administration de votre établissement va arbitrer.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de contester cette réception."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  if (!etablissementId) {
    return (
      <div className="page-content">
        <EmptyState icon={<Store size={24} />} title="Établissement introuvable" desc="Votre inscription doit être validée pour accéder à la marketplace." />
      </div>
    );
  }

  if (chargement) {
    return <div className="page-content"><SkeletonCard /></div>;
  }

  return (
    <div className="page-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <SectionHead
          eyebrow="Marketplace étudiante"
          title="Achetez et vendez entre élèves de votre établissement"
          desc="Réservé aux élèves de 16 ans ou plus. Paiement sécurisé par séquestre, remise toujours en main propre."
        />
        <Btn variant="primary" onClick={() => setShowForm((v) => !v)} leftIcon={<ImagePlus size={16} />}>
          {showForm ? "Fermer" : "Publier une annonce"}
        </Btn>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {transactionEnAttentePaiement && (
        <Card className="anim-pop-in" style={{ marginBottom: "24px", border: "1px solid color-mix(in srgb, var(--action-deep) 30%, transparent)", background: "var(--action-tint)" }}>
          <p style={{ margin: "0 0 4px", fontWeight: 700, color: "var(--action-deep)" }}>
            Paiement requis pour finaliser votre réservation
          </p>
          <p style={{ margin: "0 0 12px", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
            Le montant est sécurisé (séquestre) jusqu'à ce que vous confirmiez avoir bien reçu l'article.
          </p>
          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <KkiapayButton
              montant={transactionEnAttentePaiement.prix_paye}
              reference={transactionEnAttentePaiement.id}
              onSucces={(txId) => payerTransaction(transactionEnAttentePaiement.id, txId)}
              disabled={actionEnCoursId === transactionEnAttentePaiement.id}
            />
            <Btn variant="ghost" size="sm" loading={actionEnCoursId === transactionEnAttentePaiement.id} onClick={() => annulerReservation(transactionEnAttentePaiement.id)}>
              Annuler la réservation
            </Btn>
          </div>
        </Card>
      )}

      {showForm && (
        <Card className="anim-slide-up" style={{ marginBottom: "24px" }}>
          <form onSubmit={publier} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <Field label="Titre" required>
              <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Ex. Calculatrice scientifique Casio" />
            </Field>
            <Field label="Description" required>
              <TextArea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Field label="Catégorie" required>
                <Select value={categorie} onChange={(e) => setCategorie(e.target.value as CategorieAnnonce)}>
                  {Object.entries(LABEL_CATEGORIE).map(([valeur, libelle]) => (
                    <option key={valeur} value={valeur}>{libelle}</option>
                  ))}
                </Select>
              </Field>
              <Field label="État" required>
                <Select value={etat} onChange={(e) => setEtat(e.target.value as EtatArticle)}>
                  {Object.entries(LABEL_ETAT).map(([valeur, libelle]) => (
                    <option key={valeur} value={valeur}>{libelle}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Prix (FCFA)" required>
                <TextInput type="number" min="1" value={prix} onChange={(e) => setPrix(e.target.value)} />
              </Field>
            </div>
            <Field label="Photo(s)" required helper="Au moins une photo est obligatoire.">
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => setPhotosAEnvoyer(Array.from(e.target.files ?? []))}
                className="field-input"
              />
            </Field>
            <Btn type="submit" variant="primary" loading={enCoursPublication}>Publier</Btn>
          </form>
        </Card>
      )}

      <div style={{ marginBottom: "32px" }}>
        <SectionHead
          title="Annonces disponibles"
          desc="Uniquement les élèves de votre établissement."
        />
        <div className="flex gap-3 flex-wrap mb-4">
          <Select value={filtreCategorie} onChange={(e) => setFiltreCategorie(e.target.value as CategorieAnnonce | "")} style={{ maxWidth: "220px" }}>
            <option value="">Toutes les catégories</option>
            {Object.entries(LABEL_CATEGORIE).map(([valeur, libelle]) => (
              <option key={valeur} value={valeur}>{libelle}</option>
            ))}
          </Select>
          <Select value={filtreEtat} onChange={(e) => setFiltreEtat(e.target.value as EtatArticle | "")} style={{ maxWidth: "200px" }}>
            <option value="">Tous les états</option>
            {Object.entries(LABEL_ETAT).map(([valeur, libelle]) => (
              <option key={valeur} value={valeur}>{libelle}</option>
            ))}
          </Select>
        </div>

        {annonces.length === 0 ? (
          <EmptyState icon={<ShoppingBag size={24} />} title="Aucune annonce disponible" desc="Soyez le premier à publier un article." />
        ) : (
          <div className="space-y-3">
            {annonces.map((a) => {
              const estMoi = a.vendeur_id === utilisateur?.id;
              const photos = photosParAnnonce[a.id];
              return (
                <Card key={a.id} className="anim-float-in">
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
                    <div style={{ flex: 1, minWidth: "220px" }}>
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{a.titre}</p>
                        <Badge tone="neutral">{LABEL_CATEGORIE[a.categorie]}</Badge>
                        <Badge tone="info">{LABEL_ETAT[a.etat]}</Badge>
                      </div>
                      <p style={{ margin: "2px 0 0", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>{a.description}</p>
                      <Btn variant="ghost" size="sm" onClick={() => voirPhotos(a.id)} style={{ marginTop: "6px" }}>
                        {photos ? "Masquer les photos" : "Voir les photos"}
                      </Btn>
                      {photos && (
                        <div className="flex gap-2 flex-wrap mt-2">
                          {photos.map((p) => (
                            <img key={p.id} src={p.url} alt="" style={{ width: "84px", height: "84px", objectFit: "cover", borderRadius: "var(--radius-sm)" }} />
                          ))}
                        </div>
                      )}
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <p style={{ margin: "0 0 8px", fontWeight: 700, color: "var(--primary-deep)" }}>{a.prix.toLocaleString("fr-FR")} FCFA</p>
                      {estMoi ? (
                        <Badge tone="info">Votre annonce</Badge>
                      ) : (
                        <div className="flex gap-2 justify-end flex-wrap">
                          <Btn variant="primary" size="sm" loading={actionEnCoursId === a.id} onClick={() => reserver(a.id)}>
                            Réserver et payer
                          </Btn>
                          <Btn variant="ghost" size="sm" loading={actionEnCoursId === a.id} onClick={() => signaler(a.id)} leftIcon={<Flag size={14} />}>
                            Signaler
                          </Btn>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ marginBottom: "32px" }}>
        <SectionHead title="Mes annonces" desc="Ce que vous avez publié, tous statuts confondus." />
        {mesAnnoncesListe.length === 0 ? (
          <EmptyState icon={<Store size={24} />} title="Vous n'avez publié aucune annonce" />
        ) : (
          <div className="space-y-3">
            {mesAnnoncesListe.map((a) => (
              <Card key={a.id} className="anim-float-in">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                  <div>
                    <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{a.titre}</p>
                    <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>{a.prix.toLocaleString("fr-FR")} FCFA</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={STATUT_ANNONCE_TONE[a.statut]}>{STATUT_ANNONCE_LABEL[a.statut]}</Badge>
                    {a.statut === "disponible" && (
                      <Btn variant="ghost" size="sm" loading={actionEnCoursId === a.id} onClick={() => retirer(a.id)} leftIcon={<Trash2 size={14} />}>
                        Retirer
                      </Btn>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div>
        <SectionHead title="Mes transactions" desc="En tant qu'acheteur ou en tant que vendeur." />
        {transactions.length === 0 ? (
          <EmptyState icon={<ShoppingBag size={24} />} title="Aucune transaction en cours" />
        ) : (
          <div className="space-y-3">
            {transactions.map((t) => {
              const annonce = annonceParTransaction[t.annonce_id];
              const estAcheteur = t.acheteur_id === utilisateur?.id;
              const estVendeur = annonce?.vendeur_id === utilisateur?.id;
              return (
                <Card key={t.id} className="anim-float-in">
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", marginBottom: "8px" }}>
                    <div>
                      <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{annonce?.titre ?? "Article"}</p>
                      <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>
                        {estVendeur ? "Vous êtes le vendeur" : "Vous êtes l'acheteur"} — {t.prix_paye.toLocaleString("fr-FR")} FCFA
                      </p>
                    </div>
                    <Badge tone={STATUT_TRANSACTION_TONE[t.statut]}>{STATUT_TRANSACTION_LABEL[t.statut]}</Badge>
                  </div>

                  <div className="flex gap-2 flex-wrap items-center">
                    {estVendeur && t.statut === "paiement_confirme" && (
                      <Btn variant="primary" size="sm" loading={actionEnCoursId === t.id} onClick={() => declarer(t.id)}>
                        Déclarer la remise effectuée
                      </Btn>
                    )}
                    {estAcheteur && t.statut === "remise_declaree" && (
                      <>
                        <Btn variant="primary" size="sm" loading={actionEnCoursId === t.id} onClick={() => confirmer(t.id)}>
                          Confirmer la réception
                        </Btn>
                        <div className="flex gap-2 items-center">
                          <TextInput
                            placeholder="Motif de contestation"
                            value={motifContestationParId[t.id] ?? ""}
                            onChange={(e) => setMotifContestationParId((prev) => ({ ...prev, [t.id]: e.target.value }))}
                            style={{ minWidth: "200px" }}
                          />
                          <Btn variant="action" size="sm" loading={actionEnCoursId === t.id} onClick={() => contester(t.id)}>
                            Contester
                          </Btn>
                        </div>
                      </>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
