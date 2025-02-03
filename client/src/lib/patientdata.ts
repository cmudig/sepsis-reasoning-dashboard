export type PatientDataElement = {
  name: string;
  value?: string;
  unit?: string;
  present?: number;
  delta?: number;
  abnormal?: boolean;
  ever?: number;
  children?: PatientDataElement[];
  expanded?: boolean;
};
export type PatientData = {
  [key: string]: {
    data?: any[];
    timesteps?: {
      time: number;
      data: any;
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
