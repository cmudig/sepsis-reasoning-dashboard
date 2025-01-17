export type PatientDataElement = {
  name: string;
  value?: string;
  unit?: string;
  present?: number;
  delta?: number;
  abnormal?: boolean;
  ever?: number;
  children?: PatientDataElement[];
};
export type PatientData = {
  [key: string]: {
    data?: PatientDataElement[];
    timesteps?: {
      time: number;
      data: PatientDataElement[];
    }[];
  };
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
