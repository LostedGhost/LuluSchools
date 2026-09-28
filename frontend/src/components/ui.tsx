import type {
  ButtonHTMLAttributes,
  CSSProperties,
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
  SelectHTMLAttributes,
} from "react";
import { Children, cloneElement, isValidElement, useEffect, useId, useRef, useState, type ReactElement } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, Inbox, X } from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   Card
   ═══════════════════════════════════════════════════════════════ */

export function Card({
  children,
  className = "",
  hover = false,
  variant = "default",
  style,
  onClick,
  id,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  variant?: "default" | "soft" | "flat";
  style?: CSSProperties;
  onClick?: () => void;
  id?: string;
}) {
  const base =
    variant === "soft"
      ? "card-soft"
      : variant === "flat"
      ? "rounded-[var(--radius-lg)] bg-[var(--surface-2)] p-6"
      : "card";
  return (
    <div
      id={id}
      className={`${base} ${hover ? "card-hover cursor-pointer" : ""} ${className}`}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PageTitle
   ═══════════════════════════════════════════════════════════════ */

export function PageTitle({
  children,
  eyebrow,
}: {
  children: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="mb-6">
      {eyebrow && <p className="text-eyebrow mb-2">{eyebrow}</p>}
      <h1 className="text-headline m-0" style={{ color: "var(--ink)" }}>
        {children}
      </h1>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Boutons
   ═══════════════════════════════════════════════════════════════ */

type BtnVariant =
  | "primary"
  | "reward"
  | "action"
  | "magic"
  | "outline"
  | "ghost";
type BtnSize = "sm" | "md" | "lg";

interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: BtnVariant;
  size?: BtnSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export function Btn({
  variant = "primary",
  size = "md",
  loading = false,
  leftIcon,
  rightIcon,
  children,
  disabled,
  className = "",
  ...props
}: BtnProps) {
  const variantClass = `btn-${variant}`;
  const sizeClass = size === "sm" ? "btn-sm" : size === "lg" ? "btn-lg" : "";
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`btn ${variantClass} ${sizeClass} ${className}`}
    >
      {loading ? (
        <span
          style={{
            width: "14px",
            height: "14px",
            border: "2px solid currentColor",
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin-slow .7s linear infinite",
            display: "inline-block",
          }}
        />
      ) : leftIcon ? (
        leftIcon
      ) : null}
      {children}
      {!loading && rightIcon ? rightIcon : null}
    </button>
  );
}

/** @deprecated Utiliser <Btn variant="primary"> */
export function PrimaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`btn btn-primary ${props.className ?? ""}`}
    />
  );
}

/** @deprecated Utiliser <Btn variant="outline"> */
export function SecondaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`btn btn-outline ${props.className ?? ""}`}
    />
  );
}

/* ═══════════════════════════════════════════════════════════════
   Champs de formulaire
   ═══════════════════════════════════════════════════════════════ */

export function Field({
  label,
  children,
  error,
  helper,
  required,
  htmlFor,
}: {
  /** Id du champ, quand l'enfant n'est pas un champ unique (champ + bouton « afficher »...). */
  htmlFor?: string;
  label: string;
  children: ReactNode;
  error?: string | null;
  helper?: string;
  required?: boolean;
}) {
  // Accessibilité : l'étiquette est reliée au champ (htmlFor/id) et l'aide ou l'erreur lui
  // est annoncée (aria-describedby), quand l'enfant est un champ unique.
  const idAuto = useId();
  const unique = isValidElement(children) && typeof children.type === "string" && ["input", "select", "textarea"].includes(children.type)
    || (isValidElement(children) && [TextInput, TextArea, Select].includes(children.type as never));
  const props = unique ? (children as ReactElement<Record<string, unknown>>).props : {};
  const idChamp = (props.id as string | undefined) ?? `${idAuto}-champ`;
  const idAide = `${idAuto}-aide`;
  const champ = unique
    ? cloneElement(children as ReactElement<Record<string, unknown>>, {
        id: idChamp,
        "aria-describedby": error || helper ? idAide : undefined,
        "aria-invalid": error ? true : undefined,
        "aria-required": required || undefined,
      })
    : children;
  const cible = unique ? idChamp : htmlFor;
  const Etiquette = cible ? "label" : "span";
  // Enfant composite (champ + bouton...) : on relie l'étiquette au premier champ trouvé.
  const conteneur = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (cible || !conteneur.current) return;
    const champ = conteneur.current.querySelector<HTMLElement>("input:not([type=hidden]), select, textarea");
    const etiquette = conteneur.current.querySelector<HTMLElement>(".field-label");
    if (!champ || !etiquette) return;
    if (!champ.id) champ.id = `${idAuto}-champ`;
    etiquette.id = `${idAuto}-etiquette`;
    if (!champ.getAttribute("aria-label")) champ.setAttribute("aria-labelledby", etiquette.id);
  });
  return (
    <div className="field" ref={conteneur}>
      <Etiquette className="field-label" {...(cible ? { htmlFor: cible } : {})}>
        {label}
        {required && (
          <span style={{ color: "var(--action)", marginLeft: "4px" }} aria-hidden="true">*</span>
        )}
      </Etiquette>
      {champ}
      {error && (
        <span className="field-error" id={idAide}>
          <AlertTriangle size={14} aria-hidden="true" />
          {error}
        </span>
      )}
      {!error && helper && <span className="field-helper" id={idAide}>{helper}</span>}
    </div>
  );
}

/** Hors d'un <Field>, le texte indicatif sert de nom accessible (lecteurs d'écran). */
const nomParDefaut = (props: { id?: string; placeholder?: string }) =>
  !props.id && props.placeholder ? props.placeholder : undefined;

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      aria-label={nomParDefaut(props)}
      {...props}
      className={`field-input ${props.className ?? ""}`}
    />
  );
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      aria-label={nomParDefaut(props)}
      {...props}
      className={`field-input ${props.className ?? ""}`}
      style={{ minHeight: "100px", resize: "vertical", ...props.style }}
    />
  );
}

export function Select({
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  // Hors d'un <Field> (filtres de liste), l'option vide « Tous statuts » sert de nom
  // accessible, faute d'étiquette visible.
  const optionVide = Children.toArray(children).find(
    (o) => isValidElement<{ value?: unknown; children?: ReactNode }>(o) && o.props.value === "" && typeof o.props.children === "string",
  ) as ReactElement<{ children: string }> | undefined;
  const nom = !props.id && optionVide ? `Filtre : ${optionVide.props.children}` : undefined;
  return (
    <select aria-label={nom} {...props} className={`field-input ${props.className ?? ""}`}>
      {children}
    </select>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Feedback
   ═══════════════════════════════════════════════════════════════ */

/** Erreur affichée à l'endroit du formulaire ; elle défile jusqu'à être visible quand elle
 * apparaît (une action en bas de page ne doit pas échouer « en silence » hors de l'écran). */
export function ErrorBanner({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const texte = typeof children === "string" ? children : children ? "x" : "";
  useEffect(() => {
    if (texte) ref.current?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [texte]);
  if (!children) return null;
  return (
    <div
      ref={ref}
      className="chip chip-error rounded-[var(--radius-md)] px-4 py-3 text-sm w-full justify-start"
      role="alert"
      aria-live="assertive"
      style={{ whiteSpace: "normal", lineHeight: 1.5 }}
    >
      <span className="chip-dot" />
      {children}
    </div>
  );
}

/** Confirmation d'une action réussie : notification flottante en bas de l'écran (visible
 * quel que soit l'endroit de la page où l'action a eu lieu), qui disparaît d'elle-même. */
export function SuccessBanner({ children, duree = 6000 }: { children: ReactNode; duree?: number }) {
  const [masque, setMasque] = useState<ReactNode>(null);
  useEffect(() => {
    if (!children) {
      setMasque(null);
      return;
    }
    const t = window.setTimeout(() => setMasque(children), duree);
    return () => window.clearTimeout(t);
  }, [children, duree]);
  if (!children || masque === children) return null;
  return createPortal(
    <div className="toast chip chip-success anim-slide-up" role="status" aria-live="polite">
      <span className="chip-dot" />
      <span style={{ flex: 1 }}>{children}</span>
      <button type="button" className="toast-fermer" onClick={() => setMasque(children)} aria-label="Fermer la notification">
        <X size={14} />
      </button>
    </div>,
    document.body,
  );
}

/* ═══════════════════════════════════════════════════════════════
   Badge (statut)
   ═══════════════════════════════════════════════════════════════ */

type BadgeTone = "success" | "pending" | "error" | "info" | "magic" | "neutral";

export function Badge({
  tone = "neutral",
  children,
  dot = true,
}: {
  tone?: BadgeTone;
  children: ReactNode;
  dot?: boolean;
}) {
  return (
    <span className={`chip chip-${tone}`}>
      {dot && <span className="chip-dot" />}
      {children}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Tile KPI
   ═══════════════════════════════════════════════════════════════ */

export function KPITile({
  label,
  value,
  sub,
  accent,
  icon,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: "primary" | "reward" | "action" | "magic";
  icon?: ReactNode;
}) {
  const accentColor = accent
    ? {
        primary: "var(--primary)",
        reward: "var(--reward-deep)",
        action: "var(--action-deep)",
        magic: "var(--info-deep)",
      }[accent]
    : "var(--ink)";

  return (
    <div className="tile">
      <div className="tile-key">{label}</div>
      <div className="flex items-end gap-2">
        {icon && (
          <span style={{ color: accentColor, display: "inline-flex" }} aria-hidden="true">
            {icon}
          </span>
        )}
        <div
          className="tile-value"
          style={{ color: accentColor }}
        >
          {value}
        </div>
      </div>
      {sub && (
        <div className="monospace mt-1" style={{ fontSize: "11px" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section header
   ═══════════════════════════════════════════════════════════════ */

export function SectionHead({
  eyebrow,
  title,
  desc,
}: {
  eyebrow?: string;
  title: string;
  desc?: string;
}) {
  return (
    <div className="section-head">
      {eyebrow && <span className="text-eyebrow">{eyebrow}</span>}
      <h2 className="text-title" style={{ margin: "4px 0 6px", color: "var(--ink)" }}>
        {title}
      </h2>
      {desc && <p className="text-sm" style={{ color: "var(--ink-soft)" }}>{desc}</p>}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Empty State
   ═══════════════════════════════════════════════════════════════ */

export function EmptyState({
  icon,
  photo,
  title,
  desc,
  action,
}: {
  icon?: ReactNode;
  /** Photo optionnelle (URL) affichée au-dessus du titre à la place de l'icône -
   * réservé aux cas où une vraie photo apporte du contexte (voir utils/photosParDefaut.ts) ;
   * l'icône reste le défaut partout ailleurs (identité visuelle, voir ADR-007). */
  photo?: string;
  title: string;
  desc?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {photo ? (
        <img
          src={photo}
          alt=""
          aria-hidden="true"
          style={{ width: "100%", maxWidth: "280px", aspectRatio: "16 / 10", objectFit: "cover", borderRadius: "var(--radius-md)", marginBottom: "var(--space-3)" }}
        />
      ) : (
        <span className="empty-state-icon" aria-hidden="true">{icon ?? <Inbox size={24} />}</span>
      )}
      <p className="empty-state-title">{title}</p>
      {desc && <p className="empty-state-desc">{desc}</p>}
      {action}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Skeleton
   ═══════════════════════════════════════════════════════════════ */

export function Skeleton({
  height = "20px",
  width = "100%",
  className = "",
}: {
  height?: string;
  width?: string;
  className?: string;
}) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ height, width }}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="card" aria-busy="true" aria-label="Chargement en cours">
      <Skeleton height="12px" width="60px" className="mb-3" />
      <Skeleton height="28px" width="80%" className="mb-2" />
      <Skeleton height="14px" className="mb-1" />
      <Skeleton height="14px" width="75%" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Divider
   ═══════════════════════════════════════════════════════════════ */

export function Divider() {
  return <hr className="divider-dashed" />;
}

/* ═══════════════════════════════════════════════════════════════
   Label Text (compat legacy)
   ═══════════════════════════════════════════════════════════════ */

export function LabelText(props: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      {...props}
      className={`text-sm text-[var(--ink-faint)] ${props.className ?? ""}`}
    />
  );
}
