export function formatText(text: string): string {
  return text
    .replaceAll(/\*\*(.*?)\*\*/g, '<span style="font-weight: bold;">$1</span>')
    .replaceAll(/\*(.*?)\*/g, '<em>$1</em>')
    .replaceAll('\n', '<br/>');
}

// https://pmc.ncbi.nlm.nih.gov/articles/PMC11067312/
export function riskDescription(mean: number): string {
  if (mean <= 0.05) return 'extremely unlikely';
  else if (mean <= 0.15) return 'very unlikely';
  else if (mean <= 0.3) return 'unlikely';
  else if (mean <= 0.6) return 'possible';
  else if (mean <= 0.8) return 'likely';
  else if (mean <= 0.99) return 'very likely';
  else return 'extremely likely';
}

export function probabilityDescription(
  mean: number,
  overallMean: number
): string {
  let diff = (mean - overallMean) / overallMean;
  if (diff <= -0.25) return 'very low';
  if (diff <= -0.1) return 'low';
  if (diff <= 0.1) return 'average';
  if (diff <= 0.25) return 'high';
  return 'very high';
}
