import { describe, expect, it } from "vitest";

import { schemaFixture } from "@/test/api";

import { buildFeatures, inputColumns, validateRecord, valuesFromRecord } from "./features";

const { columns } = schemaFixture();
const names = (scenario: Parameters<typeof inputColumns>[1]) =>
  inputColumns(columns, scenario).map((c) => c.name);

describe("record features", () => {
  it("never includes the final grade, and grades only where the scenario allows", () => {
    expect(names("early")).toEqual(["sex", "absences"]);
    expect(names("mid_year")).toEqual(["sex", "absences", "G1"]);
    expect(names("full_history")).toEqual(["sex", "absences", "G1", "G2"]);
  });

  it("drops grades and the outcome from the request even if they were entered", () => {
    const values = { sex: "M", absences: "2", G1: "11", G2: "12", G3: "13", at_risk: "1" };
    expect(buildFeatures(columns, values, "early")).toEqual({ sex: "M", absences: 2 });
    expect(buildFeatures(columns, values, "full_history")).toEqual({
      sex: "M",
      absences: 2,
      G1: 11,
      G2: 12,
    });
  });

  it("validates required values, codes, integers and ranges", () => {
    expect(validateRecord(columns, {}, "mid_year")).toEqual({
      sex: "Required.",
      absences: "Required.",
      G1: "Required.",
    });
    expect(validateRecord(columns, { sex: "X", absences: "2.5", G1: "21" }, "mid_year")).toEqual({
      sex: "Choose one of the documented values.",
      absences: "Enter a whole number.",
      G1: "Must be at most 20.",
    });
    expect(validateRecord(columns, { sex: "F", absences: "-1" }, "early")).toEqual({
      absences: "Must be at least 0.",
    });
    expect(validateRecord(columns, { sex: "F", absences: "0" }, "early")).toEqual({});
  });

  it("copies a dataset record without its final grade", () => {
    expect(valuesFromRecord(columns, { sex: "F", absences: 3, G1: 9, G2: 8, G3: 7 })).toEqual({
      sex: "F",
      absences: "3",
      G1: "9",
      G2: "8",
    });
  });
});
