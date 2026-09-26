import type { TypeEtablissement } from "../types/api";

/**
 * Photos par défaut, par type d'établissement, utilisées quand aucune photo réelle
 * n'a encore été envoyée par l'A+ (voir PhotosEtablissementManager) — pour ne jamais
 * laisser une carte de présentation vide. Toutes libres de droits (licence Pexels :
 * usage commercial et non-commercial libre, aucune attribution requise — créditée
 * ici par courtoisie) et choisies pour correspondre réellement au niveau représenté
 * (écoles/salles de classe africaines, pas des photos occidentales génériques).
 * Redimensionnées via les paramètres de l'API Pexels (`?auto=compress&cs=tinysrgb&w=`)
 * plutôt que hotlink des originaux (1-4 Mo pièce).
 */
interface PhotoParDefaut {
  url: string;
  credit: string;
}

function pexels(id: number, largeur: number): string {
  return `https://images.pexels.com/photos/${id}/pexels-photo-${id}.jpeg?auto=compress&cs=tinysrgb&w=${largeur}`;
}

export const PHOTOS_PAR_DEFAUT: Record<TypeEtablissement, PhotoParDefaut[]> = {
  EP: [
    { url: pexels(35305047, 800), credit: "Speak Media Uganda — Pexels" },
    { url: pexels(35250413, 800), credit: "Speak Media Uganda — Pexels" },
  ],
  ES: [
    { url: pexels(30546833, 800), credit: "Chris Wade Ntezicimpa — Pexels" },
    { url: pexels(30058872, 800), credit: "Khalifa Yahaya — Pexels" },
  ],
  UP: [
    { url: pexels(10604063, 800), credit: "Adedire Abiodun — Pexels" },
    { url: pexels(12497063, 800), credit: "Amos Getanda — Pexels" },
  ],
};

/** Bande photo pleine largeur (landing page) - même photo que ES[1], en plus haute résolution. */
export const PHOTO_HERO_CLASSE = pexels(30058872, 1600);

/** Sélection déterministe (pas aléatoire) pour qu'un même établissement affiche
 * toujours la même photo par défaut d'un rendu à l'autre. */
export function photoParDefaut(type: TypeEtablissement, etablissementId: string): PhotoParDefaut {
  const options = PHOTOS_PAR_DEFAUT[type];
  const index = etablissementId.charCodeAt(0) % options.length;
  return options[index];
}
