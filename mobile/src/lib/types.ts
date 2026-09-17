/**
 * Data shapes shared by every mobile screen.
 *
 * The analysis types mirror `lib/api-spec/openapi.yaml`, which is the source of
 * truth. If the API contract changes, update the spec first and then this file.
 */

export type Pipeline = 'movenet' | 'opencv-motion';

export type SignalQuality = 'good' | 'limited' | 'unusable';

/** Factor scores from 0-100. `null` means "not enough signal", never zero. */
export type AnalysisFactors = {
  movementConsistency?: number | null;
  symmetry?: number | null;
  mobility?: number | null;
  activity?: number | null;
  historicalChange?: number | null;
};

export type AnalysisWeights = Partial<Record<keyof AnalysisFactors, number>>;

/** Raw measurements from the clip. These carry no interpretation. */
export type AnalysisMeasurements = {
  frameCount: number;
  durationSeconds: number;
  meanKeypointConfidence?: number | null;
  leftAnkleMotion?: number | null;
  rightAnkleMotion?: number | null;
  strideSymmetry?: number | null;
  asymmetryPercent?: number | null;
  motionMean: number;
  motionStd: number;
  motionCoverage: number;
  hipStability?: number | null;
  symmetryReliable: boolean;
};

export type AnalyzeResult = {
  ok: boolean;
  pipeline: Pipeline;
  signalQuality: SignalQuality;
  signalNote: string;
  measurements: AnalysisMeasurements;
  factors: AnalysisFactors;
  overallScore?: number | null;
  strideSymmetryScore?: number | null;
  asymmetryPercent?: number | null;
  confidence?: number | null;
  observation: string;
  limitations: string;
  concerningChange: boolean;
  usedLlm: boolean;
  weightsUsed?: AnalysisWeights;
};

export type Pet = {
  id: string;
  name: string;
  species: string;
  breed: string;
  age: string;
  weight: string;
  notes: string;
  createdAt: string;
};

export type PetInput = Omit<Pet, 'id' | 'createdAt'>;

/** One saved walk. Measurements and interpretation live side by side, never merged. */
export type Analysis = {
  id: string;
  petId: string;
  fileName: string;
  durationSeconds: number;
  createdAt: string;
  pipeline: Pipeline;
  signalQuality: SignalQuality;
  signalNote: string;
  overallScore: number | null;
  factors: AnalysisFactors;
  measurements: AnalysisMeasurements;
  weightsUsed?: AnalysisWeights;
  strideSymmetryScore: number | null;
  asymmetryPercent: number | null;
  confidence: number | null;
  observation: string;
  limitations: string;
  concerningChange: boolean;
  usedLlm: boolean;
};
