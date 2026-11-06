export type RdwRecordKind = "approval_scope" | "engine_candidate" | "gearbox_classification";

export interface RdwResearchCounts {
  sourceFiles: number;
  approvalScopes: number;
  registrationObservations: number;
  engineCandidates: number;
  gearboxClassifications: number;
  auxiliaryRows: number;
  sourceRows: number;
}

export interface RdwResearchSummary {
  id: "rdw-vag-nl-eu-type-approval-research";
  sourceId: "rdw-eu-vag-type-approval-open-data-nl";
  source: string;
  sourceUrl: string;
  license: "CC0-1.0";
  rightsStatus: "approved_by_published_CC0_license";
  attributionText: string;
  marketScope: "NL";
  applicabilityPrecision: string;
  reviewStatus: "verified_research_only";
  productionImport: false;
  productImportAllowed: false;
  ruEaeuApplicability: false;
  exactVehicleFitment: false;
  exactEngineGearboxPair: false;
  repairApplicability: false;
  diagnosticExecutionAllowed: false;
  sourceRevisions: Record<string, string>;
  sourceSnapshotSha256: string;
  databaseSha256: string;
  sourceManifestSha256: string;
  packManifestSha256: string;
  attributionSha256: string;
  rightsSha256: string;
  counts: RdwResearchCounts;
  warning: string;
}

export interface RdwResearchRow {
  id: string;
  recordKind: RdwRecordKind;
  make: string | null;
  tradeName: string | null;
  approvalNumber: string | null;
  variant: string | null;
  version: string | null;
  revision: string | null;
  vehicleCategory?: string | null;
  registrationCount?: number;
  engineDesignation?: string | null;
  engineTypeApprovalNumber?: string | null;
  displacementCc?: string | null;
  cylinders?: string | null;
  gearboxTypeClassification?: string | null;
  sourceDatasetId: string;
  sourceRevision: string;
  sourceSnapshotSha256: string;
  sourceFileSha256: string;
  sourceUrl: string | null;
  sourceRecordSha256: string;
  databaseSha256: string;
  sourceManifestSha256: string;
  packManifestSha256: string;
  marketScope: "NL";
  applicabilityPrecision: string;
  verificationStatus: string;
  exactVehicleFitment: false;
  ruEaeuApplicability: false;
  modelYear: null;
  generation: null;
  engineCode: null;
  gearboxCode: null;
  factoryVagEngineCodeClaim?: false;
  factoryVagGearboxCodeClaim?: false;
  exactEngineGearboxPair: false;
  repairApplicability: false;
  diagnosticExecutionAllowed: false;
  warning: string;
}

export function getRdwSummary(root?: string): RdwResearchSummary;
export function searchRdwApprovals(query: string, limit?: number, root?: string): RdwResearchRow[];
export function clearRdwCache(): void;
