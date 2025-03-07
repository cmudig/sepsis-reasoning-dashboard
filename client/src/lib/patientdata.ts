export type PatientDataElement = {
  name: string;
  value?: string | string[];
  unit?: string;
  present?: number;
  delta?: number;
  abnormal?: boolean;
  ever?: number;
  children?: PatientDataElement[];
  expanded?: boolean;
  hide_in_study?: boolean;
};
export type PatientDataSection = {
  data?: any[];
  timesteps?: {
    time: number;
    data: any;
  }[];
};
export type PatientData = {
  [key: string]: PatientDataSection;
};

export function dataElementMatchesFilter(
  element: PatientDataElement,
  f: string
): boolean {
  return (
    element.name.toLowerCase().includes(f.toLowerCase()) ||
    (!!element.children &&
      element.children.some((c) => dataElementMatchesFilter(c, f)))
  );
}

export function getHistoricalPatientData(
  data: PatientDataSection,
  timestepIndex: number,
  path: string[],
  maxTimesteps: number = 42
): { time: number; data: PatientDataElement | null }[] {
  if (!data.timesteps) return [];

  return data
    .timesteps!.slice(
      Math.max(0, timestepIndex + 1 - maxTimesteps),
      timestepIndex + 1
    )
    .map((timestep) => ({
      time: timestep.time,
      data:
        path
          .slice(0, path.length - 1)
          .reduce(
            (prev, childName) =>
              !!prev
                ? prev.find((e) => e.name == childName)?.children ?? null
                : null,
            timestep.data as PatientDataElement[] | null
          )
          ?.find((e) => e.name == path[path.length - 1]) ?? null,
    }));
}
