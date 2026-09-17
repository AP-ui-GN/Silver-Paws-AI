import { useEffect, useState } from 'react';
import { Check, ChevronDown, Edit3, PawPrint, Plus, Save, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'wouter';
import { type Pet } from '@/lib/storage';

type Props = { pets: Pet[]; addPet: (pet: Omit<Pet, 'id' | 'createdAt'>) => Pet; updatePet: (id: string, pet: Omit<Pet, 'id' | 'createdAt'>) => void };
type FormState = Omit<Pet, 'id' | 'createdAt'>;
const blank: FormState = { name: '', species: 'Dog', breed: '', age: '', weight: '', notes: '' };

export default function PetProfile({ pets, addPet, updatePet }: Props) {
  const [selectedId, setSelectedId] = useState(pets[0]?.id ?? 'new');
  const [form, setForm] = useState<FormState>(pets[0] ? { ...pets[0] } : blank);
  const [saved, setSaved] = useState(false);
  const selectedPet = pets.find((pet) => pet.id === selectedId);

  useEffect(() => {
    setForm(selectedPet ? { ...selectedPet } : blank);
    setSaved(false);
  }, [selectedId]); // selection is the intentional edit boundary

  const update = (key: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    // ==================================================
    // TEAM TASK: KAVIN
    // PURPOSE:
    // Show a visible message when name is blank, and when age or weight is
    // present but not a positive number. Do not save until those checks pass.
    // ==================================================
    if (!form.name.trim()) return;
    if (selectedPet) updatePet(selectedPet.id, form);
    else {
      const created = addPet(form);
      setSelectedId(created.id);
      setForm({ ...form });
    }
    setSaved(true);
  };

  return (
    <div className="page-frame max-w-5xl">
      <div className="flex flex-wrap justify-between items-end gap-5 stagger">
        <div><div className="eyebrow">The companion file</div><h1 className="display-title text-5xl mt-3">Make it<br /><span style={{ color: '#b9684d' }}>personal.</span></h1><p className="body-muted mt-4 max-w-md leading-relaxed">A little context helps every saved observation stay connected to the right pet.</p></div>
        <div className="soft-note p-3 text-xs flex items-center gap-2"><ShieldCheck size={15} /> Saved only in this browser</div>
      </div>

      {pets.length > 0 && (
        <div className="panel panel-padded mt-9 stagger-2">
          <div className="flex flex-wrap justify-between items-center gap-4">
            <div><div className="eyebrow">Profiles on this device</div><h2 className="display-title text-2xl mt-2">Choose a companion to edit</h2></div>
            <button className="btn-secondary" onClick={() => setSelectedId('new')} data-testid="button-add-pet"><Plus size={15} /> Add pet</button>
          </div>
          <div className="flex flex-wrap gap-3 mt-6">
            {pets.map((pet) => <button className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${selectedId === pet.id ? 'border-[#174946] bg-[#edf2e8]' : 'bg-transparent'}`} onClick={() => setSelectedId(pet.id)} key={pet.id} data-testid={`button-select-pet-${pet.id}`}><span className="pet-orb" style={{ width: 42, height: 42, borderRadius: 15, fontSize: 14 }}>{pet.name.slice(0, 2).toUpperCase()}</span><span><span className="font-bold text-sm block">{pet.name}</span><span className="body-muted text-xs block mt-1">{pet.breed || pet.species}</span></span>{selectedId === pet.id && <Check size={15} style={{ color: '#174946' }} />}</button>)}
          </div>
        </div>
      )}

      <form onSubmit={submit} className="grid lg:grid-cols-[.85fr_1.15fr] gap-5 mt-5 stagger-3">
        <div className="panel panel-padded" style={{ background: '#e5eee2' }}>
          <div className="pet-orb"><PawPrint size={28} /></div>
          <div className="eyebrow mt-7">{selectedPet ? 'Editing profile' : 'New profile'}</div>
          <h2 className="display-title text-3xl mt-2">{form.name || 'Your companion'}</h2>
          <p className="text-sm leading-relaxed mt-3" style={{ color: '#4f6e66' }}>The basics are enough. Notes are optional and can hold details you want to remember when reviewing a walk.</p>
          <div className="flex items-center gap-2 text-xs font-semibold mt-7" style={{ color: '#4f6e66' }}><Sparkles size={14} style={{ color: '#b9684d' }} /> Built for noticing, not diagnosing.</div>
        </div>
        <div className="panel panel-padded">
          <div className="grid sm:grid-cols-2 gap-5">
            <div className="sm:col-span-2"><label className="field-label" htmlFor="pet-name">Name <span style={{ color: '#b9684d' }}>*</span></label><input id="pet-name" className="field-input" value={form.name} onChange={(event) => update('name', event.target.value)} placeholder="e.g. Mabel" required data-testid="input-pet-name" /></div>
            <div><label className="field-label" htmlFor="pet-species">Species</label><select id="pet-species" className="field-input" value={form.species} onChange={(event) => update('species', event.target.value)} data-testid="select-pet-species"><option>Dog</option><option>Cat</option><option>Other</option></select></div>
            <div><label className="field-label" htmlFor="pet-breed">Breed</label><input id="pet-breed" className="field-input" value={form.breed} onChange={(event) => update('breed', event.target.value)} placeholder="Optional" data-testid="input-pet-breed" /></div>
            <div><label className="field-label" htmlFor="pet-age">Age <span className="body-muted font-normal">(years)</span></label><input id="pet-age" className="field-input" inputMode="decimal" value={form.age} onChange={(event) => update('age', event.target.value)} placeholder="e.g. 7" data-testid="input-pet-age" /></div>
            <div><label className="field-label" htmlFor="pet-weight">Weight <span className="body-muted font-normal">(kg)</span></label><input id="pet-weight" className="field-input" inputMode="decimal" value={form.weight} onChange={(event) => update('weight', event.target.value)} placeholder="Optional" data-testid="input-pet-weight" /></div>
            <div className="sm:col-span-2"><label className="field-label" htmlFor="pet-notes">Notes</label><textarea id="pet-notes" className="field-input min-h-28 resize-y" value={form.notes} onChange={(event) => update('notes', event.target.value)} placeholder="Anything that may help you interpret a clip later…" data-testid="textarea-pet-notes" /></div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 mt-7 pt-5 border-t">
            <p className="body-muted text-xs flex items-center gap-2"><Edit3 size={13} /> You can update this anytime.</p>
            <div className="flex items-center gap-3">{saved && <span className="text-xs font-semibold flex items-center gap-1" style={{ color: '#4f8063' }}><Check size={14} /> Saved locally</span>}<button type="submit" className="btn-primary" data-testid="button-save-pet"><Save size={15} /> Save profile</button></div>
          </div>
        </div>
      </form>
      <Link href="/analyze" className="btn-quiet mt-5" data-testid="link-pet-to-analysis">Ready? Choose a walk <ChevronDown size={15} className="-rotate-90" /></Link>
    </div>
  );
}