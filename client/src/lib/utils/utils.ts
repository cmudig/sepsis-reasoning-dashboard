export function formatText(text: string): string {
  return text
    .replaceAll(/\*\*(.*?)\*\*/g, '<span style="font-weight: bold;">$1</span>')
    .replaceAll(/\*(.*?)\*/g, '<em>$1</em>')
    .replaceAll('\n', '<br/>');
}
