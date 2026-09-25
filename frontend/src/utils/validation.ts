// Validation cote client, partagee entre les formulaires. Les formulaires du
// projet utilisent `noValidate` (controle visuel total sur les erreurs via
// `Field`/`error`), donc la validation HTML5 native ne s'applique jamais :
// chaque formulaire DOIT valider explicitement avant tout appel API.

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function estEmailValide(valeur: string): boolean {
  return EMAIL_REGEX.test(valeur.trim());
}

/** 8+ caracteres, au moins 1 majuscule et 1 chiffre (regle affichee partout dans l'UI). */
export function erreurMotDePasse(valeur: string): string | null {
  if (valeur.length < 8) return "8 caracteres minimum.";
  if (!/[A-Z]/.test(valeur)) return "Au moins une majuscule.";
  if (!/[0-9]/.test(valeur)) return "Au moins un chiffre.";
  return null;
}

export function estRempli(valeur: string | null | undefined): boolean {
  return valeur !== null && valeur !== undefined && valeur.trim().length > 0;
}

/** Date de naissance plausible : pas dans le futur, pas plus vieille que 120 ans. */
export function erreurDateNaissance(valeur: string): string | null {
  if (!estRempli(valeur)) return "Date de naissance requise.";
  const date = new Date(valeur);
  if (Number.isNaN(date.getTime())) return "Date invalide.";
  const maintenant = new Date();
  if (date > maintenant) return "La date de naissance ne peut pas être dans le futur.";
  const ilYa120Ans = new Date();
  ilYa120Ans.setFullYear(ilYa120Ans.getFullYear() - 120);
  if (date < ilYa120Ans) return "Date de naissance invalide.";
  return null;
}

/** Date/heure limite qui doit rester dans le futur (echeance de devoir, cloture de poste, etc.). */
export function erreurDateFuture(valeur: string): string | null {
  if (!estRempli(valeur)) return "Date requise.";
  const date = new Date(valeur);
  if (Number.isNaN(date.getTime())) return "Date invalide.";
  if (date <= new Date()) return "La date doit être dans le futur.";
  return null;
}

export function erreurEntierPositif(valeur: number, { min = 1, max }: { min?: number; max?: number } = {}): string | null {
  if (!Number.isFinite(valeur) || !Number.isInteger(valeur)) return "Nombre entier requis.";
  if (valeur < min) return `Doit être supérieur ou égal à ${min}.`;
  if (max !== undefined && valeur > max) return `Doit être inférieur ou égal à ${max}.`;
  return null;
}
