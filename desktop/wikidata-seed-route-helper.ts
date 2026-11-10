let bundledCatalogSeedAttempted = false;
let bundledCatalogSeedResult: ReturnType<typeof seedWikidataCandidateCatalog> | null = null;

function seedBundledCatalogOnce(dbPath: string) {
  const researchRoot = process.env.VAG_TECH_PRO_RESEARCH_DIR;
  if (!researchRoot) return { status: "skipped", reason: "research_root_not_configured" };
  if (bundledCatalogSeedAttempted) return bundledCatalogSeedResult;
  bundledCatalogSeedAttempted = true;
  try {
    bundledCatalogSeedResult = seedWikidataCandidateCatalog(dbPath, researchRoot);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown bundled catalog seed error";
    bundledCatalogSeedResult = { status: "error", reason: "bundled_candidate_seed_failed", message };
    console.error("[local-core] bundled Wikidata candidate seed failed", message);
  }
  return bundledCatalogSeedResult;
}
