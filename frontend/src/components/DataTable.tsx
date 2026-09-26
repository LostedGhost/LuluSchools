import { useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { Btn, EmptyState, Skeleton } from "./ui";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  width?: string;
}

export interface DataTableBulkAction {
  label: string;
  icon?: ReactNode;
  variant?: "primary" | "reward" | "action" | "magic" | "outline" | "ghost";
  onClick: (ids: string[]) => void;
  loading?: boolean;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  loading?: boolean;
  emptyTitle?: string;
  emptyDesc?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  filters?: ReactNode;
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelectionChange?: (ids: Set<string>) => void;
  bulkActions?: DataTableBulkAction[];
  onRowClick?: (row: T) => void;
}

/**
 * Composant de table générique (tri via colonnes déjà triées côté appelant, pagination
 * serveur ou statique, recherche dynamique, filtres custom, sélection multiple + actions
 * groupées) - socle du lot admin ministériel (UC-25/26/27/29/41/42/43/45 et écrans de
 * supervision), pensé pour être réutilisable par d'autres profils plus tard sans réécriture,
 * mais ce lot ne branche que les écrans A++ (voir cahier des charges, § avantage structurant).
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyTitle = "Aucun résultat",
  emptyDesc,
  searchValue,
  onSearchChange,
  searchPlaceholder = "Rechercher...",
  filters,
  page,
  pageSize,
  total,
  onPageChange,
  selectable = false,
  selectedIds,
  onSelectionChange,
  bulkActions,
  onRowClick,
}: DataTableProps<T>) {
  const [selectionLocale, setSelectionLocale] = useState<Set<string>>(new Set());
  const selection = selectedIds ?? selectionLocale;
  const setSelection = onSelectionChange ?? setSelectionLocale;

  const toutSelectionne = rows.length > 0 && rows.every((r) => selection.has(rowKey(r)));

  const basculerTout = () => {
    if (toutSelectionne) {
      setSelection(new Set());
    } else {
      setSelection(new Set(rows.map(rowKey)));
    }
  };

  const basculerLigne = (id: string) => {
    const suivant = new Set(selection);
    if (suivant.has(id)) suivant.delete(id);
    else suivant.add(id);
    setSelection(suivant);
  };

  const totalPages = total !== undefined && pageSize ? Math.max(1, Math.ceil(total / pageSize)) : null;
  const pageCourante = page ?? 0;

  return (
    <div>
      {(onSearchChange || filters) && (
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "16px", alignItems: "center" }}>
          {onSearchChange && (
            <div style={{ position: "relative", flex: "1 1 260px" }}>
              <Search size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--ink-faint)" }} />
              <input
                value={searchValue ?? ""}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder={searchPlaceholder}
                className="field-input"
                style={{ width: "100%", paddingLeft: "36px" }}
              />
            </div>
          )}
          {filters}
        </div>
      )}

      {selectable && bulkActions && bulkActions.length > 0 && selection.size > 0 && (
        <div
          className="anim-pop-in"
          style={{
            display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap",
            padding: "10px 14px", marginBottom: "12px", borderRadius: "var(--radius-md)",
            background: "var(--primary-tint)", border: "1px solid var(--primary)",
          }}
        >
          <span className="text-sm" style={{ fontWeight: 700, color: "var(--primary-deep)" }}>
            {selection.size} sélectionné{selection.size > 1 ? "s" : ""}
          </span>
          <div style={{ display: "flex", gap: "8px", marginLeft: "auto", flexWrap: "wrap" }}>
            {bulkActions.map((action) => (
              <Btn
                key={action.label}
                size="sm"
                variant={action.variant ?? "outline"}
                loading={action.loading}
                leftIcon={action.icon}
                onClick={() => action.onClick(Array.from(selection))}
              >
                {action.label}
              </Btn>
            ))}
          </div>
        </div>
      )}

      <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: "var(--radius-md)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm)" }}>
          <thead>
            <tr style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--border)" }}>
              {selectable && (
                <th style={{ width: "36px", padding: "10px 12px" }}>
                  <input type="checkbox" checked={toutSelectionne} onChange={basculerTout} aria-label="Tout sélectionner" />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={{ textAlign: "left", padding: "10px 12px", fontWeight: 700, color: "var(--ink-soft)", width: col.width }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                  {selectable && <td style={{ padding: "10px 12px" }} />}
                  {columns.map((col) => (
                    <td key={col.key} style={{ padding: "10px 12px" }}>
                      <Skeleton height="14px" />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} style={{ padding: 0 }}>
                  <EmptyState title={emptyTitle} desc={emptyDesc} />
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const id = rowKey(row);
                return (
                  <tr
                    key={id}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    style={{
                      borderBottom: "1px solid var(--border)",
                      cursor: onRowClick ? "pointer" : "default",
                      background: selection.has(id) ? "var(--primary-tint)" : "transparent",
                    }}
                  >
                    {selectable && (
                      <td style={{ padding: "10px 12px" }} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selection.has(id)}
                          onChange={() => basculerLigne(id)}
                          aria-label="Sélectionner la ligne"
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td key={col.key} style={{ padding: "10px 12px", color: "var(--ink)" }}>
                        {col.render(row)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {totalPages !== null && totalPages > 1 && onPageChange && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "14px", marginTop: "16px" }}>
          <Btn size="sm" variant="outline" disabled={pageCourante === 0} onClick={() => onPageChange(pageCourante - 1)}>
            <ChevronLeft size={14} /> Précédent
          </Btn>
          <span className="text-sm" style={{ color: "var(--ink-soft)" }}>
            Page {pageCourante + 1} / {totalPages} · {total} résultat{(total ?? 0) > 1 ? "s" : ""}
          </span>
          <Btn size="sm" variant="outline" disabled={pageCourante + 1 >= totalPages} onClick={() => onPageChange(pageCourante + 1)}>
            Suivant <ChevronRight size={14} />
          </Btn>
        </div>
      )}
    </div>
  );
}
