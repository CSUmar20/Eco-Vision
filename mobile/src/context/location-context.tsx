import { createContext, type ReactNode, useContext, useMemo, useState } from 'react';

type LocationContextValue = {
  jurisdiction: string | null;
  setJurisdiction: (jurisdiction: string) => void;
};

const LocationContext = createContext<LocationContextValue | null>(null);

export function LocationProvider({ children }: { children: ReactNode }) {
  const [jurisdiction, setJurisdiction] = useState<string | null>(null);
  const value = useMemo(() => ({ jurisdiction, setJurisdiction }), [jurisdiction]);

  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}

export function useLocationPreference(): LocationContextValue {
  const value = useContext(LocationContext);

  if (!value) {
    throw new Error('useLocationPreference must be used inside LocationProvider.');
  }

  return value;
}
