import { api, getAccessToken, rafraichirUneFois } from "./client";
import type { MessageElProfessorChat, PersonaElProfessor, SessionElProfessorOut } from "../types/api";

/* El Professor — interface de conversation commune aux 4 personas (élève, enseignant,
   tuteur, famille). Les réponses arrivent en flux (SSE) : on les lit avec fetch, axios ne
   sachant pas exposer un corps de réponse au fil de l'eau dans le navigateur. */

export interface ResultatQuestion {
  message_utilisateur: MessageElProfessorChat;
  message_assistant: MessageElProfessorChat;
}

export class ErreurElProfessor extends Error {}

async function envoyer(url: string, corps: FormData, signal?: AbortSignal): Promise<Response> {
  const appel = (jeton: string | null) =>
    fetch(url, {
      method: "POST",
      body: corps,
      signal,
      headers: jeton ? { Authorization: `Bearer ${jeton}` } : undefined,
    });
  let reponse = await appel(getAccessToken());
  if (reponse.status === 401) {
    const jeton = await rafraichirUneFois();
    if (!jeton) {
      window.location.href = "/connexion";
      throw new ErreurElProfessor("Votre session a expiré, reconnectez-vous.");
    }
    reponse = await appel(jeton);
  }
  return reponse;
}

async function messageDeReponse(reponse: Response): Promise<string> {
  try {
    const corps = await reponse.json();
    if (corps?.error?.message) return corps.error.message as string;
  } catch {
    /* corps non JSON */
  }
  if (reponse.status === 429) return "Vous avez posé beaucoup de questions : réessayez dans un moment.";
  return "El Professor n'a pas pu répondre, veuillez réessayer.";
}

export async function poserQuestionEnFlux(
  persona: PersonaElProfessor,
  sessionId: string,
  question: string,
  fichier: File | null,
  onTexte: (morceau: string) => void,
  signal?: AbortSignal,
): Promise<ResultatQuestion> {
  const corps = new FormData();
  corps.append("question", question);
  if (fichier) corps.append("fichier", fichier);

  const reponse = await envoyer(`/api/v1/el-professor/${persona}/sessions/${sessionId}/flux`, corps, signal);
  if (!reponse.ok || !reponse.body) throw new ErreurElProfessor(await messageDeReponse(reponse));

  const lecteur = reponse.body.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  for (;;) {
    const { done, value } = await lecteur.read();
    if (done) break;
    tampon += decodeur.decode(value, { stream: true });
    let separation = tampon.indexOf("\n\n");
    while (separation !== -1) {
      const bloc = tampon.slice(0, separation);
      tampon = tampon.slice(separation + 2);
      separation = tampon.indexOf("\n\n");
      let evenement = "";
      let donnees = "";
      for (const ligne of bloc.split("\n")) {
        if (ligne.startsWith("event: ")) evenement = ligne.slice(7);
        else if (ligne.startsWith("data: ")) donnees += ligne.slice(6);
      }
      if (!donnees) continue;
      const charge = JSON.parse(donnees);
      if (evenement === "delta") onTexte(charge.texte as string);
      else if (evenement === "erreur") throw new ErreurElProfessor(charge.message as string);
      else if (evenement === "fin") return charge as ResultatQuestion;
    }
  }
  throw new ErreurElProfessor("La connexion a été interrompue avant la fin de la réponse. Réessayez.");
}

export function renommerConversation(persona: PersonaElProfessor, sessionId: string, sujet: string) {
  return api.patch<{ id: string; sujet: string | null }>(`/el-professor/${persona}/sessions/${sessionId}`, { sujet });
}

export function supprimerConversation(persona: PersonaElProfessor, sessionId: string) {
  return api.delete(`/el-professor/${persona}/sessions/${sessionId}`);
}

export function listerMesConversationsEleve() {
  return api.get<SessionElProfessorOut[]>("/el-professor/eleve/sessions");
}

export function ouvrirConversationEleve(coursId?: string, sujet?: string) {
  return api.post<SessionElProfessorOut>("/el-professor/eleve/sessions", {
    cours_id: coursId ?? null,
    sujet: sujet ?? null,
  });
}

/** Lecture à voix haute (synthèse vocale FreeLLM), renvoie un fichier audio WAV. */
export async function syntheseVocale(texte: string): Promise<Blob> {
  const { data } = await api.post<Blob>("/el-professor/synthese-vocale", { texte }, { responseType: "blob" });
  return data;
}
