"use client";

import { Field, SelectControl, controlClass } from "@/components/ui/Field";
import type { ColumnInfo } from "@/lib/api";
import type { FormErrors, FormValues } from "@/lib/features";

const GROUP_ORDER = [
  "Grades",
  "School and study",
  "Social and lifestyle",
  "Health",
  "Family background",
  "Demographic",
];

function hintFor(column: ColumnInfo): string | undefined {
  if (column.role === "prior_grade") return "0–20, as recorded for this period";
  if (column.name === "absences")
    return `Number of school absences (${column.minimum}–${column.maximum})`;
  if (column.name === "failures") return "Number of past class failures (3 = 3 or more)";
  if (!column.allowed_values.length && column.minimum !== null && column.maximum !== null)
    return `${column.minimum}–${column.maximum}`;
  return undefined;
}

/** Columns grouped in display order (grades and school factors first). */
export function groupColumns(columns: ColumnInfo[]) {
  const groups = GROUP_ORDER.map((group) => ({
    group,
    columns: columns.filter((c) => c.group === group),
  })).filter((g) => g.columns.length);
  const other = columns.filter((c) => !GROUP_ORDER.includes(c.group));
  if (other.length) groups.push({ group: "Other", columns: other });
  return groups;
}

/** One input per column, grouped as in the data dictionary; codes are the UCI codes. */
export function RecordForm({
  columns,
  values,
  errors,
  onChange,
  idPrefix = "field",
}: {
  columns: ColumnInfo[];
  values: FormValues;
  errors: FormErrors;
  onChange: (name: string, value: string) => void;
  idPrefix?: string;
}) {
  const groups = groupColumns(columns);

  return (
    <div className="space-y-6">
      {groups.map(({ group, columns: cols }) => (
        <fieldset key={group} className="min-w-0">
          <legend className="mb-3 text-[13px] font-semibold text-text">{group}</legend>
          <div className="grid gap-x-4 gap-y-3.5 sm:grid-cols-2 xl:grid-cols-3">
            {cols.map((column) => {
              const id = `${idPrefix}-${column.name}`;
              const error = errors[column.name];
              const hint = hintFor(column);
              const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
              return (
                <Field key={column.name} id={id} label={column.label} hint={hint} error={error}>
                  {column.allowed_values.length ? (
                    <SelectControl
                      id={id}
                      name={column.name}
                      value={values[column.name] ?? ""}
                      invalid={Boolean(error)}
                      aria-describedby={describedBy}
                      onChange={(event) => onChange(column.name, event.target.value)}
                    >
                      <option value="">Choose…</option>
                      {column.allowed_values.map((a) => (
                        <option key={String(a.code)} value={String(a.code)}>
                          {String(a.code) === a.label ? a.label : `${a.label} (${a.code})`}
                        </option>
                      ))}
                    </SelectControl>
                  ) : (
                    <input
                      id={id}
                      name={column.name}
                      type="number"
                      inputMode="numeric"
                      step={1}
                      min={column.minimum ?? undefined}
                      max={column.maximum ?? undefined}
                      value={values[column.name] ?? ""}
                      aria-invalid={Boolean(error) || undefined}
                      aria-describedby={describedBy}
                      onChange={(event) => onChange(column.name, event.target.value)}
                      className={controlClass(Boolean(error))}
                    />
                  )}
                </Field>
              );
            })}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
