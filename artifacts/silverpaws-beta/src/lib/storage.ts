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

export type AnalysisStatus = 'complete' | 'processing' | 'ready';

export type Analysis = {
  id: string;
  petId: string;
  fileName: string;
  durationSeconds: number;
  createdAt: string;
  status: AnalysisStatus;
  strideSymmetryScore?: number;
  asymmetryPercent?: number;
  confidence?: number;
  observation?: string;
  limitations?: string;
  source?: string;
  license?: string;
  sourceUrl?: string;
};

const PETS_KEY = 'silverpaws:pets';
const ANALYSES_KEY = 'silverpaws:analyses';

const starterPet: Pet = {
  id: 'pet-mabel',
  name: 'Mabel',
  species: 'Dog',
  breed: 'Cavalier King Charles Spaniel',
  age: '7',
  weight: '9.4',
  notes: 'A little cautious on slick floors.',
  createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 28).toISOString(),
};

const starterAnalyses: Analysis[] = [
  {
    id: 'analysis-starter',
    petId: 'pet-mabel',
    fileName: 'mabel-garden-walk.mp4',
    durationSeconds: 18,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
    status: 'complete',
    strideSymmetryScore: 86,
    asymmetryPercent: 7,
    confidence: 78,
    observation: 'Mabel’s stride looked broadly even in this clip, with a small difference in rear-leg timing.',
    limitations: 'This is an educational observation from one camera angle and one moment in time. It is not a diagnosis.',
  },
];

function read<T>(key: string, fallback: T): T {
  try {
    const value = window.localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Local-first beta should keep working even when storage is unavailable.
  }
}

export function getPets() {
  const pets = read<Pet[]>(PETS_KEY, []);
  if (pets.length) return pets;
  write(PETS_KEY, [starterPet]);
  return [starterPet];
}

export function getAnalyses() {
  return read<Analysis[]>(ANALYSES_KEY, starterAnalyses);
}

export function savePets(pets: Pet[]) {
  write(PETS_KEY, pets);
}

export function saveAnalyses(analyses: Analysis[]) {
  write(ANALYSES_KEY, analyses);
}

export function makeId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}