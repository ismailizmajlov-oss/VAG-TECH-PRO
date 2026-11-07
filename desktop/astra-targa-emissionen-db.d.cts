export interface AstraTargaCounts {
  approvalPowertrainVariantRows: number;
  sourceDefinedVariantLinkRows: number;
  exactVagFactoryCodePairRows: number;
  exactVehicleFitmentRows: number;
  ruEaeuApplicabilityRows: number;
}
export interface AstraTargaSummary {
  id: string; sourceId: string; source: string; sourceUrl: string; rightsStatus: string; license: string;
  attributionText: string; marketScope: "CH"; applicabilityPrecision: string; reviewStatus: string;
  productionImport: false; productImportAllowed: false; ruEaeuApplicability: false;
  exactVagFactoryCodePair: false; exactVehicleFitment: false; repairApplicability: false; diagnosticExecutionAllowed: false;
  sourceRevision: string; sourceFileSha256: string; sourceSnapshotSha256: string; databaseSha256: string;
  sourceManifestSha256: string; packManifestSha256: string; sourceRegistryManifestSha256: string;
  counts: AstraTargaCounts; note: string;
}
export interface AstraTargaRow {
  id: number; sourceRowNumber: number; sourceRecordSha256: string; sourceRecordLocator: string; sourceFileSha256: string;
  approvalNumber: string; make: string; type: string | null; gearboxClassification: string | null;
  finalDriveRatio: string | null; engineMake: string | null; engineType: string | null; engineConstruction: string | null;
  fuel: string | null; displacementCc: string | null; powerKw: number | null; powerRpm: string | null;
  torqueNm: string | null; torqueRpm: string | null; emissionControl: string | null; drive: string | null;
  emissionsCode: string | null; homologationDate: string | null; marketScope: "CH"; applicabilityPrecision: string;
  sourceDefinedVariantLink: true; exactVagFactoryCodePair: false; exactVehicleFitment: false; ruEaeuApplicability: false;
  modelYear: null; generation: null; engineTypeStatus: string; gearboxStatus: string;
  sourceRevision: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string;
  sourceUrl: string; warning: string;
}
export function getAstraTargaSummary(root?: string): AstraTargaSummary;
export function searchAstraTargaRows(query: string, limit?: number, root?: string): AstraTargaRow[];
