/**
 * Ouvre/télécharge un blob reçu d'axios (responseType: "blob") - nécessaire pour les
 * PDF de ticketerie (UC-54/68, lot admin établissement) : un lien <a href> direct ne
 * porterait pas l'en-tête d'authentification Bearer, contrairement à cet appel axios
 * déjà intercepté (voir api/client.ts).
 */
export function ouvrirBlobPdf(blob: Blob, nomFichier: string): void {
  const url = URL.createObjectURL(blob);
  const lien = document.createElement("a");
  lien.href = url;
  lien.target = "_blank";
  lien.rel = "noopener noreferrer";
  lien.download = nomFichier;
  document.body.appendChild(lien);
  lien.click();
  document.body.removeChild(lien);
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
