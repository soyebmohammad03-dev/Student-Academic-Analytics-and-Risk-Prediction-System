"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Section } from "@/components/ui/Section";
import { SegmentedControl, Toolbar, ToolbarItem } from "@/components/ui/SegmentedControl";
import {
  type Cohort,
  type CohortOverlap as Overlap,
  type DatasetQuality,
  type DatasetRecords,
  type DatasetSchema,
  type DatasetSummary,
  datasetPath,
} from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { cohortOptions, useCohort } from "@/lib/useCohort";

import { CohortOverlap } from "./CohortOverlap";
import { DataDictionary } from "./DataDictionary";
import { DataQuality } from "./DataQuality";
import { DatasetOverview } from "./DatasetOverview";
import { RecordsTable } from "./RecordsTable";
import { DataUnavailable } from "./states";

export const PAGE_SIZE = 25;
const SEARCH_DELAY_MS = 250;

/** Keep only data that belongs to the selected cohort, never a stale one. */
function forCohort<T extends { cohort: Cohort }>(data: T | undefined, cohort: Cohort) {
  return data?.cohort === cohort ? data : undefined;
}

export function DataExplorer() {
  const [cohort, setCohort] = useCohort();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const next = searchInput.trim();
    if (next === query) return;
    const timer = setTimeout(() => {
      setQuery(next);
      setPage(1);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [searchInput, query]);

  const summary = useApi<DatasetSummary>(datasetPath("summary", cohort), reloadKey);
  const quality = useApi<DatasetQuality>(datasetPath("quality", cohort), reloadKey);
  const schema = useApi<DatasetSchema>(datasetPath("schema", cohort), reloadKey);
  const records = useApi<DatasetRecords>(
    datasetPath("records", cohort, { page, pageSize: PAGE_SIZE, search: query }),
    reloadKey,
  );
  const overlap = useApi<Overlap>("/dataset/overlap", reloadKey);

  function selectCohort(next: Cohort) {
    setCohort(next);
    setPage(1);
    setSearchInput("");
    setQuery("");
  }

  const error = summary.error ?? quality.error ?? schema.error ?? records.error;

  return (
    <div className="space-y-12 sm:space-y-14">
      <PageHeader
        eyebrow="Analysis"
        title="Data Explorer"
        description="Browse the two published student cohorts, check how clean the data is, and see what every attribute means — before any statistics or modelling."
      >
        <Toolbar className="mt-6">
          <ToolbarItem label="Cohort">
            <SegmentedControl
              label="Cohort"
              options={cohortOptions}
              value={cohort}
              onChange={selectCohort}
            />
          </ToolbarItem>
        </Toolbar>
      </PageHeader>

      {error ? (
        <DataUnavailable error={error} onRetry={() => setReloadKey((k) => k + 1)} />
      ) : (
        <>
          <Section title="Overview">
            <DatasetOverview summary={forCohort(summary.data, cohort)} />
          </Section>

          <Section
            title="Data quality"
            description="Every value is checked against the UCI documentation."
          >
            <DataQuality quality={forCohort(quality.data, cohort)} />
          </Section>

          <Section
            title="Records"
            description="One row per student. Row numbers are positions in the file, not student IDs."
          >
            <RecordsTable
              records={forCohort(records.data, cohort)}
              columns={forCohort(schema.data, cohort)?.columns}
              loading={records.loading}
              searchInput={searchInput}
              onSearchInput={setSearchInput}
              onPage={setPage}
            />
          </Section>

          <Section
            title="Data dictionary"
            description="All 33 attributes as documented by UCI, with the values observed in this cohort."
          >
            <DataDictionary columns={forCohort(schema.data, cohort)?.columns} />
          </Section>

          <Section
            title="Students in both cohorts"
            description="The files share no student ID, so overlap can only be estimated."
          >
            {overlap.error ? (
              <p className="px-1 text-[13px] text-text-secondary">{overlap.error.message}</p>
            ) : (
              <CohortOverlap overlap={overlap.data} />
            )}
          </Section>
        </>
      )}
    </div>
  );
}
