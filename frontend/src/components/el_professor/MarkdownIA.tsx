import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

/* Rendu des réponses d'El Professor : Markdown (listes, gras, tableaux) et formules LaTeX.
   Chargé à la demande (React.lazy) pour ne pas alourdir les autres pages. react-markdown
   ignore tout HTML brut : une réponse du modèle ne peut pas injecter de balise. */

/** Les modèles écrivent aussi les formules entre \( \) et \[ \] : on les ramène à la
    syntaxe $ / $$ que comprend remark-math, sans toucher aux blocs de code. */
function normaliserFormules(texte: string): string {
  return texte
    .split(/(```[\s\S]*?```|`[^`\n]*`)/g)
    .map((morceau, index) =>
      index % 2 === 1
        ? morceau
        : morceau
            .replace(/\\\[([\s\S]+?)\\\]/g, (_, formule: string) => `\n$$\n${formule.trim()}\n$$\n`)
            .replace(/\\\(([\s\S]+?)\\\)/g, (_, formule: string) => `$${formule.trim()}$`),
    )
    .join("");
}

export default function MarkdownIA({ texte }: { texte: string }) {
  return (
    <div className="markdown-ia">
      <Markdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="markdown-ia-table">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {normaliserFormules(texte)}
      </Markdown>
    </div>
  );
}
