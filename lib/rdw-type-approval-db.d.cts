export interface RdwTypeApprovalCounts {
  vehicle_variants: number;
  engine_candidates: number;
  transmission_candidates: number;
  approval_revision_candidates: number;
  manufacturer_designation_candidates: number;
  unique_source_row_pair_candidates: number;
  ambiguous_or_incomplete_pair_keys: number;
}

export interface RdwTypeApprovalSummary {
  status: string;
  sourceId: string;
  sourceRevision?: string;
  dataLicense?: string;
  sourceUrl?: string;
  licenseUrl?: string;
  marketScope?: string[];
  applicabilityPrecision?: string;
  verificationStatus?: string;
  counts: RdwTypeApprovalCounts | null;
  databaseSha256?: string;
  sourceSnapshotSha256?: string;
  metadataBundleSha256?: string;
  exactVehicleFitment?: false;
  ruEaeuApplicability?: false;
  vagFactoryEngineCodeVerified?: false;
  vagFactoryGearboxCodeVerified?: false;
  diagnosticExecutionAllowed?: false;
  limitations?: string[];
  error?: string;
}

export interface RdwTypeApprovalCandidate {
  make: string;
  model: string;
  manufacturerTypeCode: string | null;
  typeApprovalNumber: string;
  variantCode: string;
  executionCode: string;
  firstRegistrationSeen: string | null;
  lastRegistrationSeen: string | null;
  revisionNumber: string | null;
  revisionStartDate: string | null;
  revisionEndDate: string | null;
  rdwMotorcode: string | null;
  engineCodeNamespace: "RDW.motorcode";
  rdwTransmissionTypeCode: string | null;
  transmissionCodeNamespace: "RDW.codetypeversnellingsbak";
  gearCountMin: string | null;
  gearCountMax: string | null;
  pairingStatus: string;
  engineRowCount: number;
  transmissionRowCount: number;
  manufacturerTradeName: string | null;
  manufacturerTypeDesignation: string | null;
  marketScope: string;
  applicabilityPrecision: string;
  verificationStatus: string;
  sourceId: string;
  sourceRevision: string;
  pairingConfirmed: false;
  exactVehicleFitment: false;
  ruEaeuApplicability: false;
  vagFactoryEngineCodeVerified: false;
  vagFactoryGearboxCodeVerified: false;
}

export interface RdwTypeApprovalSearchResult {
  status: string;
  summary?: RdwTypeApprovalSummary;
  results: RdwTypeApprovalCandidate[];
}

export interface RdwTypeApprovalDb {
  getSummary(): RdwTypeApprovalSummary;
  search(query?: string, limit?: number): RdwTypeApprovalSearchResult;
  verify(): { ok: boolean; status: string; error?: string; packDir?: string; dbPath?: string; manifest?: unknown; source?: unknown };
}

export interface RdwTypeApprovalDbOptions {
  cwd?: string;
  packDir?: string;
  lockPath?: string;
  registerPath?: string;
  refresh?: boolean;
}

export function createRdwTypeApprovalDb(options?: RdwTypeApprovalDbOptions): RdwTypeApprovalDb;
export function verifyRdwTypeApprovalPack(options?: RdwTypeApprovalDbOptions): { ok: boolean; status: string; error?: string; packDir?: string; dbPath?: string; manifest?: unknown; source?: unknown };
export function getRdwTypeApprovalSummary(): RdwTypeApprovalSummary;
export function searchRdwTypeApprovalCandidates(query?: string, limit?: number): RdwTypeApprovalSearchResult;
