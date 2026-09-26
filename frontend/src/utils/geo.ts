/** Lien Google Maps sans clé API (format documenté officiel) - ouvre directement les
 * directions/la position, jamais un widget embarqué (pas de clé API configurée). */
export function lienGoogleMaps(latitude: number, longitude: number): string {
  return `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;
}
