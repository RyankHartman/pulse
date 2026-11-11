import type { AppData } from "./types";

const FILES = ["meta", "integrity", "forecast", "anomalies", "cohorts", "summary", "sql"] as const;

async function load<T>(name: string): Promise<T> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${name}.json`);
  if (!response.ok) throw new Error(`Could not load ${name}.json (${response.status}). Run: python pipeline/build.py`);
  return (await response.json()) as T;
}

export async function loadAll(): Promise<AppData> {
  const [meta, integrity, forecast, anomalies, cohorts, summary, sql] = await Promise.all(
    FILES.map((name) => load(name)),
  );
  return { meta, integrity, forecast, anomalies, cohorts, summary, sql } as AppData;
}
