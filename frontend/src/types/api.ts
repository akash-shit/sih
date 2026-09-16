export type ChangeStatus = 'OPEN' | 'CONFIRMED' | 'REJECTED' | 'SUPPRESSED';

export type ChangeType =
  | 'construction'
  | 'vegetation_clearance'
  | 'water_extent_change'
  | 'road_development'
  | 'no_clear_category'
  | string;

export interface Stats {
  aoi_count: number;
  scene_count: number;
  tile_count: number;
  vector_count: number;
  candidates_scored: number;
  candidates_promoted: number;
  candidates_confirmed: number;
  candidates_suppressed: number;
  processing_version: string | null;
  last_run: string | null;
}

export interface AOI {
  aoi_id: string;
  name: string;
  bbox: [number, number, number, number];
  start_date: string | null;
  end_date: string | null;
  scene_count: number;
  tile_count: number;
  mosaic_thumbnail_url: string | null;
  last_activity: string | null;
}

export interface TimelineEntry {
  date: string;
  scene_id: string;
  sensor: string | null;
  cloud_fraction: number | null;
  tile_count: number;
  acquisition_date_source: string | null;
  thumbnail_url: string | null;
}

export interface MosaicTile {
  tile_id: string;
  vector_id: number | null;
  x: number;
  y: number;
  width: number;
  height: number;
  cluster_id: number | null;
  has_change_candidate: boolean;
}

export interface Mosaic {
  aoi_id: string;
  date: string;
  image_url: string;
  width: number;
  height: number;
  tiles: MosaicTile[];
}

export interface TileDetail {
  tile_id: string;
  vector_id: number | null;
  aoi_id: string;
  scene_id: string;
  date: string;
  acquisition_date_source: string | null;
  sensor: string | null;
  lat: number;
  lon: number;
  bbox: [number, number, number, number];
  ndvi_mean: number | null;
  ndwi_mean: number | null;
  cloud_fraction: number | null;
  valid_pixel_fraction: number | null;
  cluster_id: number | null;
  processing_version: string | null;
  thumbnail_url: string | null;
}

export interface SearchResult {
  tile_id: string;
  vector_id: number | null;
  reference_vector_id?: number | null;
  aoi_id: string;
  aoi_name: string | null;
  date: string;
  similarity: number;
  lat: number;
  lon: number;
  thumbnail_url: string | null;
  reference_thumbnail_url: string | null;
  reference_date: string | null;
  analysis_available: boolean;
  change_candidate_id: string | null;
}

export interface CompareResult {
  difference_image_url: string | null;
}

export interface ChangeCandidate {
  candidate_id: string;
  vector_id: number | null;
  tile_id: string;
  aoi_id: string;
  aoi_name: string | null;
  before_date: string;
  after_date: string;
  embedding_drift: number | null;
  spectral_delta: number | null;
  combined_score: number | null;
  change_type: ChangeType | null;
  confidence: number | null;
  status: ChangeStatus;
  suppressed: boolean;
  suppression_reason: string | null;
  earliest_supported_date: string | null;
  before_thumbnail_url: string | null;
  after_thumbnail_url: string | null;
  before_source_available: boolean;
  after_source_available: boolean;
  source_unavailable_reason: string | null;
}

export interface ReviewQuality {
  total_candidates: number;
  displayable_candidates: number;
  cloud_suppressed: number;
  snow_suppressed: number;
  pixel_quality_suppressed: number;
  seasonal_suppressed: number;
  below_threshold_suppressed: number;
  other_quality_suppressed: number;
  source_imagery_unavailable: number;
}

export interface NdviPoint {
  date: string;
  ndvi_mean: number | null;
  ndwi_mean: number | null;
  cloud_fraction: number | null;
}

export interface ChangeEvidence {
  before_date: string;
  after_date: string;
  change_region: string | null;
  visual_difference_summary: string;
  before_ndvi: number | null;
  after_ndvi: number | null;
  ndvi_change: number | null;
  spectral_change: number | null;
  semantic_change: number | null;
  quality: string;
  confound_information: string[];
  candidate_interpretation: string;
  confidence: number | null;
  difference_image_url: string | null;
  changed_fraction: number | null;
  centroid_x: number | null;
  centroid_y: number | null;
  narrative: string;
}

export interface ChangeDetail extends ChangeCandidate {
  before_image_url: string | null;
  after_image_url: string | null;
  lat: number;
  lon: number;
  bbox: [number, number, number, number];
  ndvi_series: NdviPoint[];
  quality_notes: string[];
  acquisition_date_source: string | null;
  processing_version: string | null;
  evidence: ChangeEvidence;
}

export interface ReviewDecision {
  decision: 'CONFIRM' | 'REJECT';
  reason?: string;
}

export interface ReviewResponse {
  ok: boolean;
}

export interface AuditLogEntry {
  log_id: string;
  candidate_id: string;
  tile_id: string | null;
  decision: string;
  reason: string | null;
  created_at: string;
}

export interface Cluster {
  cluster_id: number;
  member_count: number;
  aoi_ids: string[];
  representative_thumbnail_url: string | null;
  label: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface ClusterMember {
  tile_id: string;
  vector_id: number | null;
  aoi_id: string;
  date: string;
  thumbnail_url: string | null;
}

export interface OnboardScene {
  scene_id: string;
  date: string | null;
  status: string;
  message: string | null;
}

export interface OnboardJob {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  progress: number;
  message: string | null;
  aoi_id: string | null;
  scenes_found: number | null;
  scenes_ingested: number | null;
  scenes_failed: number | null;
  tiles_added: number | null;
  warnings: string[];
  scenes: OnboardScene[];
}

export interface TextSearchRequest {
  query: string;
  aoi_id?: string;
  date?: string;
  date_from?: string;
  date_to?: string;
  k?: number;
}

export interface VelocityPoint {
  date_pair: { before: string; after: string };
  velocity: number;
  source: string;
}

export interface TemporalSignature {
  series: VelocityPoint[];
  velocities: number[];
  score_sources: string[];
  acceleration: number | null;
  trend: string;
  latest_velocity: number | null;
}

export interface VelocityTile extends TemporalSignature {
  tile_id: string;
}

export interface StorylineProfile {
  short: number | null;
  seasonal: number | null;
  long: number | null;
  score_sources: Record<string, string | null>;
}

export interface Storyline {
  profile: StorylineProfile;
  velocities: number[];
  stage: string;
}
