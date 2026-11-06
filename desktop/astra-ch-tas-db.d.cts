export interface AstraChTasCounts {
  approvals: number;
  emissionsGearboxRows: number;
  linkedScopeRows: number;
  exactScopeLinks: number;
  wildcardScopeLinks: number;
  unlinkedScopeRows: number;
}
export interface AstraChTasSummary {
  id: string; sourceId: string; source: string; sourceUrl: string; rightsEvidenceUrl: string;
  rightsStatus: string; license: string; attributionText: string; marketScope: "CH";
  applicabilityPrecision: string; reviewStatus: string; productionImport: false;
  ruEaeuApplicability: false; exactVehicleFitment: false; repairApplicability: false;
  diagnosticExecutionAllowed: false; sourceRevision: string; sourceSnapshotDate: string;
  sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string;
  packManifestSha256: string; attributionSha256: string; rightsSha256: string;
  counts: AstraChTasCounts; note: string;
}
export interface AstraChTasRow {
  id: number; approvalNumber: string; make: string; commercialName: string | null;
  typeDesignation: string | null; variant: string | null; version: string | null;
  engineTypeDesignation: string | null; stampedEngineMarking: string | null; fuelType: string | null;
  engineCapacityCc: number | null; maximumNetPower: string | null; driveType: string | null;
  gearboxNumber: string | null; gearboxClass: string | null; gearboxMapping: string | null;
  gearboxVersionScope: string | null; gearboxScopeStatus: string | null; relationPrecision: string;
  gearboxClassificationKind: string; marketScope: "CH"; applicabilityPrecision: string;
  modelYear: null; engineCode: null; gearboxCode: null; factoryVagEngineCodeClaim: false;
  factoryVagGearboxCodeClaim: false; productionFitmentClaim: false; repairApplicability: false;
  diagnosticExecutionAllowed: false; sourceRevision: string; sourceSnapshotSha256: string;
  databaseSha256: string; sourceManifestSha256: string; sourceRecordSha256: string;
  gearboxRecordSha256: string | null; sourceUrl: string; warning: string;
}
export function getAstraSummary(root?: string): AstraChTasSummary;
export function searchAstraApprovals(query: string, limit?: number, root?: string): AstraChTasRow[];
