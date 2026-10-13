/**
 * Form model for one student record, built from GET /dataset/schema.
 *
 * Leakage rules enforced here (and again by the API):
 * - the target G3 and the derived label at_risk are never inputs;
 * - G1 and G2 are inputs only in the scenarios that allow them.
 */

import type { CellValue, ColumnInfo } from "./api";
import { type Features, allowedGrades } from "./models";
import type { Scenario } from "./risk";

export type FormValues = Record<string, string>;
export type FormErrors = Record<string, string>;

/** Names that must never be sent as predictors. */
export const FORBIDDEN_INPUTS = ["G3", "at_risk"] as const;

/** Columns the form shows for a scenario, in schema order. */
export function inputColumns(columns: ColumnInfo[], scenario: Scenario): ColumnInfo[] {
  const grades: string[] = allowedGrades(scenario);
  return columns.filter((c) =>
    c.role === "feature" ? true : c.role === "prior_grade" ? grades.includes(c.name) : false,
  );
}

export function validateRecord(
  columns: ColumnInfo[],
  values: FormValues,
  scenario: Scenario,
): FormErrors {
  const errors: FormErrors = {};
  for (const column of inputColumns(columns, scenario)) {
    const raw = (values[column.name] ?? "").trim();
    if (raw === "") {
      errors[column.name] = "Required.";
      continue;
    }
    if (column.allowed_values.length) {
      if (!column.allowed_values.some((a) => String(a.code) === raw)) {
        errors[column.name] = "Choose one of the documented values.";
      }
      continue;
    }
    if (column.dtype === "integer") {
      if (!/^-?\d+$/.test(raw)) {
        errors[column.name] = "Enter a whole number.";
        continue;
      }
      const value = Number(raw);
      if (column.minimum !== null && value < column.minimum) {
        errors[column.name] = `Must be at least ${column.minimum}.`;
      } else if (column.maximum !== null && value > column.maximum) {
        errors[column.name] = `Must be at most ${column.maximum}.`;
      }
    }
  }
  return errors;
}

/** The request's `features`: only the scenario's inputs, typed as in the UCI files. */
export function buildFeatures(
  columns: ColumnInfo[],
  values: FormValues,
  scenario: Scenario,
): Features {
  const features: Features = {};
  for (const column of inputColumns(columns, scenario)) {
    const raw = (values[column.name] ?? "").trim();
    features[column.name] = column.dtype === "integer" ? Number(raw) : raw;
  }
  for (const name of FORBIDDEN_INPUTS) delete features[name];
  return features;
}

/** Form values from a dataset record. The outcome (G3) is never copied. */
export function valuesFromRecord(
  columns: ColumnInfo[],
  record: Record<string, CellValue>,
): FormValues {
  const values: FormValues = {};
  for (const column of columns) {
    if (column.role === "target") continue;
    const value = record[column.name];
    if (value !== null && value !== undefined) values[column.name] = String(value);
  }
  return values;
}
