// Liste les textes affiches de l'interface (texte JSX, chaines litterales hors code) avec
// leur position, au format JSON. Sert a l'audit de la langue (accents, formulations) :
//   node scripts/textes_affiches.cjs > textes.json
// Exclus : className/style/key/type/href/to, imports, types litteraux, cles d'objet,
// comparaisons (===, !==), arguments d'appels API et chaines sans espace.
const fs = require("fs");
const path = require("path");
const ts = require("typescript");

const RACINE = path.join(__dirname, "..", "src");
const ATTRIBUTS_TECHNIQUES = new Set(["className", "style", "key", "type", "href", "to", "id", "name", "role", "accept",
  "autoComplete", "inputMode", "pattern", "rel", "target", "src", "htmlFor", "method", "encType", "viewBox", "d", "fill",
  "stroke", "data-testid"]);
const APPELS_TECHNIQUES = new Set(["get", "post", "patch", "put", "delete", "append", "getItem", "setItem", "removeItem",
  "querySelector", "addEventListener", "require", "startsWith", "endsWith", "includes", "split", "replace", "match",
  "classList", "cn", "clsx", "Error"]);

function fichiers(dossier) {
  return fs.readdirSync(dossier, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dossier, e.name);
    if (e.isDirectory()) return fichiers(p);
    return /\.(tsx?|)$/.test(e.name) && !e.name.endsWith(".d.ts") ? [p] : [];
  });
}

const sortie = [];
for (const f of fichiers(RACINE)) {
  const src = fs.readFileSync(f, "utf8");
  const sf = ts.createSourceFile(f, src, ts.ScriptTarget.Latest, true, f.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const ajouter = (debut, fin, texte, genre) => {
    if (!/[A-Za-z]{2,}/.test(texte)) return;
    sortie.push({ fichier: path.relative(RACINE, f), debut, fin, texte, genre, ligne: sf.getLineAndCharacterOfPosition(debut).line + 1 });
  };
  const exclu = (n) => {
    const p = n.parent;
    if (!p) return false;
    if (ts.isImportDeclaration(p) || ts.isExportDeclaration(p) || ts.isLiteralTypeNode(p)) return true;
    if (ts.isJsxAttribute(p) && ATTRIBUTS_TECHNIQUES.has(p.name.getText())) return true;
    if (ts.isJsxExpression(p) && p.parent && ts.isJsxAttribute(p.parent) && ATTRIBUTS_TECHNIQUES.has(p.parent.name.getText())) return true;
    if (ts.isPropertyAssignment(p) && p.name === n) return true;
    if (ts.isElementAccessExpression(p)) return true;
    if (ts.isBinaryExpression(p) && [ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken,
      ts.SyntaxKind.EqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsToken].includes(p.operatorToken.kind)) return true;
    if (ts.isCaseClause(p)) return true;
    if (ts.isCallExpression(p)) {
      const nom = ts.isPropertyAccessExpression(p.expression) ? p.expression.name.getText() : p.expression.getText();
      if (APPELS_TECHNIQUES.has(nom)) return true;
    }
    return false;
  };
  const visiter = (n) => {
    if (ts.isJsxText(n)) {
      const t = n.getText();
      if (t.trim()) ajouter(n.getStart(), n.getEnd(), t, "jsx");
    } else if ((ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) && !exclu(n)) {
      if (n.text.includes(" ")) ajouter(n.getStart() + 1, n.getEnd() - 1, src.slice(n.getStart() + 1, n.getEnd() - 1), "chaine");
    } else if (ts.isTemplateExpression(n) && !exclu(n)) {
      const morceaux = [n.head, ...n.templateSpans.map((s) => s.literal)];
      for (const m of morceaux) {
        const debut = m.getStart() + 1;
        const fin = m.getEnd() - (ts.isTemplateTail(m) ? 1 : 2);
        const t = src.slice(debut, fin);
        if (t.includes(" ")) ajouter(debut, fin, t, "gabarit");
      }
    }
    ts.forEachChild(n, visiter);
  };
  visiter(sf);
}
process.stdout.write(JSON.stringify(sortie));
