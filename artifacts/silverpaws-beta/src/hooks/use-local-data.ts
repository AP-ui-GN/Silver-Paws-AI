import { useCallback, useEffect, useState } from 'react';
import {
  type Analysis,
  type Pet,
  getAnalyses,
  getPets,
  makeId,
  saveAnalyses,
  savePets,
} from '@/lib/storage';

export function useLocalData() {
  const [pets, setPets] = useState<Pet[]>(() => getPets());
  const [analyses, setAnalyses] = useState<Analysis[]>(() => getAnalyses());

  useEffect(() => {
    savePets(pets);
  }, [pets]);

  useEffect(() => {
    saveAnalyses(analyses);
  }, [analyses]);

  const addPet = useCallback((pet: Omit<Pet, 'id' | 'createdAt'>) => {
    const next: Pet = { ...pet, id: makeId('pet'), createdAt: new Date().toISOString() };
    setPets((current) => [...current, next]);
    return next;
  }, []);

  const updatePet = useCallback((id: string, updates: Omit<Pet, 'id' | 'createdAt'>) => {
    setPets((current) => current.map((pet) => pet.id === id ? { ...pet, ...updates } : pet));
  }, []);

  const addAnalysis = useCallback((analysis: Omit<Analysis, 'id' | 'createdAt'>) => {
    const next: Analysis = { ...analysis, id: makeId('analysis'), createdAt: new Date().toISOString() };
    setAnalyses((current) => [next, ...current]);
    return next;
  }, []);

  const updateAnalysis = useCallback((id: string, updates: Partial<Analysis>) => {
    setAnalyses((current) => current.map((analysis) => analysis.id === id ? { ...analysis, ...updates } : analysis));
  }, []);

  const deleteAnalysis = useCallback((id: string) => {
    setAnalyses((current) => current.filter((analysis) => analysis.id !== id));
  }, []);

  return { pets, analyses, addPet, updatePet, addAnalysis, updateAnalysis, deleteAnalysis };
}