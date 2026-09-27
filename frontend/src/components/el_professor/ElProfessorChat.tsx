import {
  Suspense,
  lazy,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ClipboardEvent,
  type DragEvent,
  type Dispatch,
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
  type SetStateAction,
} from "react";
import {
  ArrowLeft,
  Check,
  Copy,
  FileText,
  ImageIcon,
  Loader2,
  MessageSquarePlus,
  Mic,
  MicOff,
  Paperclip,
  Pencil,
  RotateCcw,
  Search,
  Send,
  Sparkles,
  Square,
  Trash2,
  TriangleAlert,
  Volume2,
  X,
} from "lucide-react";
import {
  ErreurElProfessor,
  poserQuestionEnFlux,
  renommerConversation,
  supprimerConversation,
  syntheseVocale,
} from "../../api/el_professor";
import { messageErreur } from "../../api/client";
import type { MessageElProfessorChat, PersonaElProfessor } from "../../types/api";
import "./ElProfessorChat.css";

const MarkdownIA = lazy(() => import("./MarkdownIA"));

export interface ConversationChat {
  id: string;
  sujet: string | null;
  /** Titre affiché tant que la conversation n'a ni sujet ni première question. */
  titreParDefaut: string;
  /** Contexte affiché sous le titre (cours, élève concerné...). */
  contexte?: string | null;
  creeLe: string;
  messages: MessageElProfessorChat[];
  /** Fil familial pas encore rejoint par l'enfant. */
  enAttente?: boolean;
  /** Donnée propre à la page (ex. identifiant de l'élève concerné). */
  reference?: string | null;
}

interface Props {
  persona: PersonaElProfessor;
  /** Rôle des messages écrits par l'utilisateur connecté (eleve, enseignant, tuteur). */
  roleUtilisateur: string;
  conversations: ConversationChat[];
  setConversations: Dispatch<SetStateAction<ConversationChat[]>>;
  chargement: boolean;
  activeId: string | null;
  setActiveId: (id: string | null) => void;
  /** Formulaire d'ouverture d'une conversation, propre à chaque rôle. */
  formulaireNouvelle: (fermer: () => void) => ReactNode;
  peutGerer?: (c: ConversationChat) => boolean;
  /** Fil familial : libellé de l'autre participant humain. */
  libelleAuteur?: (role: string) => string | null;
  /** Bandeau au-dessus du fil (ex. invitation familiale à rejoindre). */
  bandeau?: (c: ConversationChat) => ReactNode;
  /** Raison pour laquelle on ne peut pas encore écrire, ou null. */
  ecritureBloquee?: (c: ConversationChat) => string | null;
  suggestions: string[];
  tutoiement?: boolean;
}

const MAX_OCTETS_PIECE_JOINTE = 10 * 1024 * 1024;
const TYPES_ACCEPTES = ["image/png", "image/jpeg", "image/webp", "application/pdf"];

interface EnvoiEnCours {
  conversationId: string;
  question: string;
  fichier: File | null;
  texte: string;
}

interface EchecEnvoi {
  conversationId: string;
  message: string;
  question: string;
  fichier: File | null;
}

function titreConversation(c: ConversationChat): string {
  if (c.sujet) return c.sujet;
  const premiere = c.messages.find((m) => m.role !== "assistant");
  if (premiere) return premiere.contenu.length > 60 ? `${premiere.contenu.slice(0, 57)}…` : premiere.contenu;
  return c.titreParDefaut;
}

function derniereActivite(c: ConversationChat): string {
  return c.messages.length > 0 ? c.messages[c.messages.length - 1].created_at : c.creeLe;
}

function dateCourte(iso: string): string {
  const date = new Date(iso);
  const aujourdHui = new Date();
  if (date.toDateString() === aujourdHui.toDateString()) {
    return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

/** Texte lisible à voix haute : sans syntaxe Markdown ni LaTeX, borné à 2 500 caractères. */
function texteAPrononcer(contenu: string): string {
  const brut = contenu
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\$\$?([^$]+)\$\$?/g, "$1")
    .replace(/\\[()[\]]/g, "")
    .replace(/\\[a-zA-Z]+/g, " ")
    .replace(/[*_#>`|~]/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\u26A0\uFE0F?|\u{1F49B}/gu, "")
    .replace(/\s+/g, " ")
    .trim();
  if (brut.length <= 2500) return brut;
  const coupe = brut.slice(0, 2500);
  const finPhrase = coupe.lastIndexOf(". ");
  return finPhrase > 1500 ? coupe.slice(0, finPhrase + 1) : coupe;
}

/* Dictée vocale : API Web Speech du navigateur (FreeLLM ne transcrit pas l'audio). */
interface ReconnaissanceVocale {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}
type ConstructeurReconnaissance = new () => ReconnaissanceVocale;

function constructeurReconnaissance(): ConstructeurReconnaissance | null {
  const w = window as unknown as {
    SpeechRecognition?: ConstructeurReconnaissance;
    webkitSpeechRecognition?: ConstructeurReconnaissance;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function PieceJointe({ nom, type }: { nom: string; type?: string | null }) {
  return (
    <span className="elp-piece">
      {type === "application/pdf" ? <FileText size={14} /> : <ImageIcon size={14} />}
      <span className="elp-piece-nom">{nom}</span>
    </span>
  );
}

function Reponse({ texte }: { texte: string }) {
  return (
    <Suspense fallback={<p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{texte}</p>}>
      <MarkdownIA texte={texte} />
    </Suspense>
  );
}

export function ElProfessorChat({
  persona,
  roleUtilisateur,
  conversations,
  setConversations,
  chargement,
  activeId,
  setActiveId,
  formulaireNouvelle,
  peutGerer = () => true,
  libelleAuteur,
  bandeau,
  ecritureBloquee,
  suggestions,
  tutoiement = false,
}: Props) {
  const [recherche, setRecherche] = useState("");
  const [nouvelleOuverte, setNouvelleOuverte] = useState(false);
  const [vueMobile, setVueMobile] = useState<"liste" | "fil">(activeId ? "fil" : "liste");
  const [question, setQuestion] = useState("");
  const [fichier, setFichier] = useState<File | null>(null);
  const [erreurComposeur, setErreurComposeur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState<EnvoiEnCours | null>(null);
  const [echec, setEchec] = useState<EchecEnvoi | null>(null);
  // Rattachés à une conversation : en changer les referme d'eux-mêmes.
  const [renommageEtat, setRenommageEtat] = useState<{ id: string; valeur: string } | null>(null);
  const [suppressionId, setSuppressionId] = useState<string | null>(null);
  const [erreurGestion, setErreurGestion] = useState<string | null>(null);
  const [copieId, setCopieId] = useState<string | null>(null);
  const [lecture, setLecture] = useState<{ id: string; etat: "chargement" | "lecture" } | null>(null);
  const [dictee, setDictee] = useState(false);
  const [survol, setSurvol] = useState(false);

  const filRef = useRef<HTMLDivElement>(null);
  const zoneTexteRef = useRef<HTMLTextAreaElement>(null);
  const entreeFichierRef = useRef<HTMLInputElement>(null);
  const annulationRef = useRef<AbortController | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audiosRef = useRef(new Map<string, string>());
  const reconnaissanceRef = useRef<ReconnaissanceVocale | null>(null);
  const colleEnBasRef = useRef(true);

  const dicteeDisponible = useMemo(() => constructeurReconnaissance() !== null, []);
  const conversationActive = conversations.find((c) => c.id === activeId) ?? null;
  const envoiActif = envoi && envoi.conversationId === activeId ? envoi : null;
  const echecActif = echec && echec.conversationId === activeId ? echec : null;
  const blocage = conversationActive && ecritureBloquee ? ecritureBloquee(conversationActive) : null;

  const listeTriee = useMemo(() => {
    const filtre = recherche.trim().toLowerCase();
    return [...conversations]
      .filter((c) => !filtre || titreConversation(c).toLowerCase().includes(filtre) || (c.contexte ?? "").toLowerCase().includes(filtre))
      .sort((a, b) => derniereActivite(b).localeCompare(derniereActivite(a)));
  }, [conversations, recherche]);

  // Libère les URL d'aperçu et d'audio à la fermeture de la page.
  useEffect(() => {
    const audios = audiosRef.current;
    return () => {
      audios.forEach((url) => URL.revokeObjectURL(url));
      audioRef.current?.pause();
      annulationRef.current?.abort();
      reconnaissanceRef.current?.stop();
    };
  }, []);

  const apercuImage = useMemo(
    () => (fichier && fichier.type.startsWith("image/") ? URL.createObjectURL(fichier) : null),
    [fichier],
  );
  useEffect(
    () => () => {
      if (apercuImage) URL.revokeObjectURL(apercuImage);
    },
    [apercuImage],
  );

  // Défilement automatique, sauf si l'utilisateur est remonté lire plus haut.
  useEffect(() => {
    const fil = filRef.current;
    if (fil && colleEnBasRef.current) fil.scrollTop = fil.scrollHeight;
  }, [conversationActive?.messages.length, envoiActif?.texte, activeId]);

  useEffect(() => {
    colleEnBasRef.current = true;
  }, [activeId]);
  const renommage = renommageEtat && renommageEtat.id === activeId ? renommageEtat.valeur : null;
  const setRenommage = (valeur: string | null) =>
    setRenommageEtat(valeur === null || !activeId ? null : { id: activeId, valeur });
  const confirmationSuppression = suppressionId !== null && suppressionId === activeId;
  const setConfirmationSuppression = (oui: boolean) => setSuppressionId(oui ? activeId : null);

  const ajusterHauteur = () => {
    const zone = zoneTexteRef.current;
    if (!zone) return;
    zone.style.height = "auto";
    zone.style.height = `${Math.min(zone.scrollHeight, 200)}px`;
  };
  useEffect(ajusterHauteur, [question]);

  const choisirFichier = (candidat: File | null | undefined) => {
    setErreurComposeur(null);
    if (!candidat) return;
    if (!TYPES_ACCEPTES.includes(candidat.type)) {
      setErreurComposeur("Seules les images (PNG, JPEG, WebP) et les PDF peuvent être joints.");
      return;
    }
    if (candidat.size > MAX_OCTETS_PIECE_JOINTE) {
      setErreurComposeur("La pièce jointe dépasse 10 Mo.");
      return;
    }
    setFichier(candidat);
  };

  const selectionner = (id: string) => {
    setErreurGestion(null);
    setActiveId(id);
    setVueMobile("fil");
    setNouvelleOuverte(false);
  };

  const envoyer = useCallback(
    async (texteQuestion: string, piece: File | null) => {
      if (!conversationActive || envoi) return;
      const conversationId = conversationActive.id;
      setEchec(null);
      setErreurComposeur(null);
      setEnvoi({ conversationId, question: texteQuestion, fichier: piece, texte: "" });
      setQuestion("");
      setFichier(null);
      colleEnBasRef.current = true;
      const annulation = new AbortController();
      annulationRef.current = annulation;
      try {
        const resultat = await poserQuestionEnFlux(
          persona,
          conversationId,
          texteQuestion,
          piece,
          (morceau) => setEnvoi((prec) => (prec ? { ...prec, texte: prec.texte + morceau } : prec)),
          annulation.signal,
        );
        setConversations((prec) =>
          prec.map((c) =>
            c.id === conversationId
              ? { ...c, messages: [...c.messages, resultat.message_utilisateur, resultat.message_assistant] }
              : c,
          ),
        );
      } catch (err) {
        const interrompue = err instanceof DOMException && err.name === "AbortError";
        setEchec({
          conversationId,
          question: texteQuestion,
          fichier: piece,
          message: interrompue
            ? "Réponse interrompue."
            : err instanceof ErreurElProfessor
              ? err.message
              : "Connexion impossible avec El Professor. Vérifiez votre connexion puis réessayez.",
        });
      } finally {
        annulationRef.current = null;
        setEnvoi(null);
      }
    },
    [conversationActive, envoi, persona, setConversations],
  );

  const soumettre = (e?: FormEvent) => {
    e?.preventDefault();
    const texte = question.trim();
    if (!texte || blocage) return;
    void envoyer(texte, fichier);
  };

  const toucheClavier = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    const tactile = window.matchMedia("(pointer: coarse)").matches;
    if (e.key === "Enter" && !e.shiftKey && !tactile && !e.nativeEvent.isComposing) {
      e.preventDefault();
      soumettre();
    }
  };

  const coller = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const image = Array.from(e.clipboardData.files).find((f) => f.type.startsWith("image/"));
    if (image) {
      e.preventDefault();
      choisirFichier(image);
    }
  };

  const deposer = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setSurvol(false);
    if (!blocage) choisirFichier(e.dataTransfer.files[0]);
  };

  const basculerDictee = () => {
    if (dictee) {
      reconnaissanceRef.current?.stop();
      return;
    }
    const Constructeur = constructeurReconnaissance();
    if (!Constructeur) return;
    const reconnaissance = new Constructeur();
    reconnaissance.lang = "fr-FR";
    reconnaissance.interimResults = false;
    reconnaissance.continuous = true;
    const base = question.trim();
    let dicte = "";
    reconnaissance.onresult = (evenement) => {
      for (let i = evenement.resultIndex; i < evenement.results.length; i++) {
        if (evenement.results[i].isFinal) dicte += `${evenement.results[i][0].transcript} `;
      }
      setQuestion(`${base}${base ? " " : ""}${dicte.trim()}`);
    };
    reconnaissance.onend = () => setDictee(false);
    reconnaissance.onerror = () => setDictee(false);
    reconnaissanceRef.current = reconnaissance;
    reconnaissance.start();
    setDictee(true);
  };

  const copier = async (message: MessageElProfessorChat) => {
    try {
      await navigator.clipboard.writeText(message.contenu);
      setCopieId(message.id);
      window.setTimeout(() => setCopieId((id) => (id === message.id ? null : id)), 1800);
    } catch {
      /* presse-papiers refusé par le navigateur */
    }
  };

  const ecouter = async (message: MessageElProfessorChat) => {
    if (lecture?.id === message.id) {
      audioRef.current?.pause();
      setLecture(null);
      return;
    }
    audioRef.current?.pause();
    setLecture({ id: message.id, etat: "chargement" });
    try {
      let url = audiosRef.current.get(message.id);
      if (!url) {
        url = URL.createObjectURL(await syntheseVocale(texteAPrononcer(message.contenu)));
        audiosRef.current.set(message.id, url);
      }
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => setLecture(null);
      await audio.play();
      setLecture({ id: message.id, etat: "lecture" });
    } catch (err) {
      setLecture(null);
      setErreurGestion(messageErreur(err, "La lecture à voix haute est indisponible pour le moment."));
    }
  };

  const validerRenommage = async (e: FormEvent) => {
    e.preventDefault();
    if (!conversationActive || renommage === null) return;
    const sujet = renommage.trim();
    if (!sujet) {
      setRenommage(null);
      return;
    }
    try {
      await renommerConversation(persona, conversationActive.id, sujet);
      setConversations((prec) => prec.map((c) => (c.id === conversationActive.id ? { ...c, sujet } : c)));
      setRenommage(null);
    } catch (err) {
      setErreurGestion(messageErreur(err, "Impossible de renommer cette conversation."));
    }
  };

  const supprimer = async () => {
    if (!conversationActive) return;
    try {
      await supprimerConversation(persona, conversationActive.id);
      setConversations((prec) => prec.filter((c) => c.id !== conversationActive.id));
      setActiveId(null);
      setVueMobile("liste");
    } catch (err) {
      setErreurGestion(messageErreur(err, "Impossible de supprimer cette conversation."));
    }
  };

  const vous = tutoiement ? "tu" : "vous";

  const bulle = (m: MessageElProfessorChat) => {
    if (m.role === "assistant") {
      const sensible = m.contenu.includes("⚠️") || m.contenu.includes("💛");
      return (
        <div key={m.id} className="elp-ligne elp-ligne-ia">
          <span className="elp-avatar" aria-hidden="true">
            <Sparkles size={16} />
          </span>
          <div className="elp-bulle-ia">
            {sensible && (
              <div className="elp-sensible">
                <TriangleAlert size={14} /> Situation sensible — l'administration est prévenue
              </div>
            )}
            <Reponse texte={m.contenu} />
            <div className="elp-actions-message">
              <button type="button" onClick={() => copier(m)} aria-label="Copier la réponse" title="Copier">
                {copieId === m.id ? <Check size={14} /> : <Copy size={14} />}
              </button>
              <button
                type="button"
                onClick={() => ecouter(m)}
                aria-label={lecture?.id === m.id ? "Arrêter la lecture" : "Écouter la réponse"}
                title={lecture?.id === m.id ? "Arrêter" : "Écouter"}
              >
                {lecture?.id === m.id && lecture.etat === "chargement" ? (
                  <Loader2 size={14} className="elp-rotation" />
                ) : lecture?.id === m.id ? (
                  <Square size={14} />
                ) : (
                  <Volume2 size={14} />
                )}
              </button>
            </div>
          </div>
        </div>
      );
    }
    const estMoi = m.role === roleUtilisateur;
    const auteur = !estMoi && libelleAuteur ? libelleAuteur(m.role) : null;
    return (
      <div key={m.id} className={`elp-ligne ${estMoi ? "elp-ligne-moi" : "elp-ligne-autre"}`}>
        <div className={estMoi ? "elp-bulle-moi" : "elp-bulle-autre"}>
          {auteur && <span className="elp-auteur">{auteur}</span>}
          <p>{m.contenu}</p>
          {m.piece_jointe_nom && <PieceJointe nom={m.piece_jointe_nom} type={m.piece_jointe_type} />}
        </div>
      </div>
    );
  };

  return (
    <div className={`elp ${vueMobile === "fil" ? "elp-mobile-fil" : "elp-mobile-liste"}`}>
      {/* ─── Liste des conversations ─── */}
      <aside className="elp-liste" aria-label="Conversations">
        <button type="button" className="elp-nouvelle" onClick={() => setNouvelleOuverte((o) => !o)}>
          <MessageSquarePlus size={16} /> Nouvelle conversation
        </button>
        {nouvelleOuverte && (
          <div className="elp-formulaire-nouvelle">
            {formulaireNouvelle(() => {
              setNouvelleOuverte(false);
              setVueMobile("fil");
            })}
          </div>
        )}
        {conversations.length > 3 && (
          <label className="elp-recherche">
            <Search size={14} aria-hidden="true" />
            <input value={recherche} onChange={(e) => setRecherche(e.target.value)} placeholder="Rechercher" aria-label="Rechercher une conversation" />
          </label>
        )}
        <div className="elp-liste-items">
          {chargement && <p className="elp-vide">Chargement…</p>}
          {!chargement && listeTriee.length === 0 && (
            <p className="elp-vide">{recherche ? "Aucun résultat." : "Aucune conversation pour l'instant."}</p>
          )}
          {listeTriee.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`elp-item ${c.id === activeId ? "elp-item-actif" : ""}`}
              onClick={() => selectionner(c.id)}
              aria-current={c.id === activeId ? "true" : undefined}
            >
              <span className="elp-item-titre">{titreConversation(c)}</span>
              <span className="elp-item-meta">
                {c.contexte && <span className="elp-item-contexte">{c.contexte}</span>}
                <span>{dateCourte(derniereActivite(c))}</span>
              </span>
            </button>
          ))}
        </div>
      </aside>

      {/* ─── Fil de la conversation ─── */}
      <section
        className={`elp-fil-zone ${survol ? "elp-survol" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          if (conversationActive && !blocage) setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={deposer}
      >
        {!conversationActive ? (
          <div className="elp-accueil">
            <span className="elp-accueil-icone" aria-hidden="true">
              <Sparkles size={28} />
            </span>
            <h2>Bonjour, je suis El Professor</h2>
            <p>
              {conversations.length > 0
                ? `Choisis${tutoiement ? "" : "sez"} une conversation ou ouvre${tutoiement ? "" : "z"}-en une nouvelle.`
                : `Ouvre${tutoiement ? "" : "z"} une conversation pour commencer.`}
            </p>
            <button type="button" className="elp-nouvelle elp-nouvelle-accueil" onClick={() => setNouvelleOuverte(true)}>
              <MessageSquarePlus size={16} /> Nouvelle conversation
            </button>
          </div>
        ) : (
          <>
            <header className="elp-entete">
              <button type="button" className="elp-retour" onClick={() => setVueMobile("liste")} aria-label="Retour aux conversations">
                <ArrowLeft size={18} />
              </button>
              {renommage !== null ? (
                <form onSubmit={validerRenommage} className="elp-renommage">
                  <input
                    autoFocus
                    value={renommage}
                    maxLength={200}
                    onChange={(e) => setRenommage(e.target.value)}
                    onKeyDown={(e) => e.key === "Escape" && setRenommage(null)}
                    aria-label="Nouveau titre"
                  />
                  <button type="submit" aria-label="Valider le titre">
                    <Check size={16} />
                  </button>
                  <button type="button" onClick={() => setRenommage(null)} aria-label="Annuler">
                    <X size={16} />
                  </button>
                </form>
              ) : (
                <div className="elp-entete-titre">
                  <h2>{titreConversation(conversationActive)}</h2>
                  {conversationActive.contexte && <span>{conversationActive.contexte}</span>}
                </div>
              )}
              {peutGerer(conversationActive) && renommage === null && (
                <div className="elp-entete-actions">
                  {confirmationSuppression ? (
                    <>
                      <span>Supprimer ?</span>
                      <button type="button" className="elp-danger" onClick={supprimer}>
                        Oui
                      </button>
                      <button type="button" onClick={() => setConfirmationSuppression(false)}>
                        Non
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => setRenommage(titreConversation(conversationActive))}
                        aria-label="Renommer la conversation"
                        title="Renommer"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmationSuppression(true)}
                        aria-label="Supprimer la conversation"
                        title="Supprimer"
                      >
                        <Trash2 size={16} />
                      </button>
                    </>
                  )}
                </div>
              )}
            </header>
            {erreurGestion && (
              <div className="elp-erreur" role="alert">
                {erreurGestion}
                <button type="button" onClick={() => setErreurGestion(null)} aria-label="Fermer">
                  <X size={14} />
                </button>
              </div>
            )}
            {bandeau?.(conversationActive)}

            <div
              className="elp-fil"
              ref={filRef}
              onScroll={(e) => {
                const el = e.currentTarget;
                colleEnBasRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
              }}
              aria-live="polite"
            >
              {conversationActive.messages.length === 0 && !envoiActif && (
                <div className="elp-suggestions">
                  <p>
                    {tutoiement ? "Pose ta question" : "Posez votre question"}, ou commence{tutoiement ? "" : "z"} par un exemple :
                  </p>
                  <div>
                    {suggestions.map((s) => (
                      <button key={s} type="button" onClick={() => !blocage && void envoyer(s, null)} disabled={!!blocage}>
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {conversationActive.messages.map(bulle)}
              {envoiActif && (
                <>
                  <div className="elp-ligne elp-ligne-moi">
                    <div className="elp-bulle-moi">
                      <p>{envoiActif.question}</p>
                      {envoiActif.fichier && <PieceJointe nom={envoiActif.fichier.name} type={envoiActif.fichier.type} />}
                    </div>
                  </div>
                  <div className="elp-ligne elp-ligne-ia">
                    <span className="elp-avatar" aria-hidden="true">
                      <Sparkles size={16} />
                    </span>
                    <div className="elp-bulle-ia">
                      {envoiActif.texte ? (
                        <Reponse texte={envoiActif.texte} />
                      ) : (
                        <span className="elp-reflexion" aria-label="El Professor réfléchit">
                          <span />
                          <span />
                          <span />
                          <em>{envoiActif.fichier ? "El Professor lit ta pièce jointe…" : "El Professor réfléchit…"}</em>
                        </span>
                      )}
                    </div>
                  </div>
                </>
              )}
              {echecActif && (
                <div className="elp-echec" role="alert">
                  <span>{echecActif.message}</span>
                  <button type="button" onClick={() => void envoyer(echecActif.question, echecActif.fichier)} disabled={!!envoi}>
                    <RotateCcw size={14} /> Réessayer
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setQuestion(echecActif.question);
                      setFichier(echecActif.fichier);
                      setEchec(null);
                    }}
                  >
                    <Pencil size={14} /> Modifier
                  </button>
                </div>
              )}
            </div>

            {blocage ? (
              <p className="elp-bloque">{blocage}</p>
            ) : (
              <form className="elp-composeur" onSubmit={soumettre}>
                {(fichier || erreurComposeur) && (
                  <div className="elp-composeur-piece">
                    {fichier && (
                      <span className="elp-piece elp-piece-brouillon">
                        {apercuImage ? <img src={apercuImage} alt="" /> : <FileText size={14} />}
                        <span className="elp-piece-nom">{fichier.name}</span>
                        <button type="button" onClick={() => setFichier(null)} aria-label="Retirer la pièce jointe">
                          <X size={12} />
                        </button>
                      </span>
                    )}
                    {erreurComposeur && <span className="elp-composeur-erreur">{erreurComposeur}</span>}
                  </div>
                )}
                <div className="elp-composeur-ligne">
                  <input
                    ref={entreeFichierRef}
                    type="file"
                    accept={TYPES_ACCEPTES.join(",")}
                    hidden
                    onChange={(e) => {
                      choisirFichier(e.target.files?.[0]);
                      e.target.value = "";
                    }}
                  />
                  <button
                    type="button"
                    className="elp-outil"
                    onClick={() => entreeFichierRef.current?.click()}
                    aria-label="Joindre une image ou un PDF"
                    title="Joindre une image ou un PDF"
                    disabled={!!envoi}
                  >
                    <Paperclip size={18} />
                  </button>
                  <textarea
                    ref={zoneTexteRef}
                    rows={1}
                    value={question}
                    maxLength={4000}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={toucheClavier}
                    onPaste={coller}
                    placeholder={tutoiement ? "Écris ta question…" : "Écrivez votre question…"}
                    aria-label="Question pour El Professor"
                  />
                  {dicteeDisponible && (
                    <button
                      type="button"
                      className={`elp-outil ${dictee ? "elp-outil-actif" : ""}`}
                      onClick={basculerDictee}
                      aria-label={dictee ? "Arrêter la dictée" : "Dicter la question"}
                      title={dictee ? "Arrêter la dictée" : "Dicter"}
                      disabled={!!envoi}
                    >
                      {dictee ? <MicOff size={18} /> : <Mic size={18} />}
                    </button>
                  )}
                  {envoi ? (
                    <button
                      type="button"
                      className="elp-envoyer"
                      onClick={() => annulationRef.current?.abort()}
                      aria-label="Arrêter la réponse"
                      title="Arrêter"
                    >
                      <Square size={16} />
                    </button>
                  ) : (
                    <button type="submit" className="elp-envoyer" disabled={!question.trim()} aria-label="Envoyer">
                      <Send size={16} />
                    </button>
                  )}
                </div>
                <p className="elp-mention">
                  El Professor peut se tromper : vérifie{tutoiement ? "" : "z"} les informations importantes. Entrée pour envoyer,
                  Maj+Entrée pour aller à la ligne. {vous === "tu" ? "Tu peux" : "Vous pouvez"} joindre une photo ou un PDF (10 Mo max).
                </p>
              </form>
            )}
          </>
        )}
      </section>
    </div>
  );
}
