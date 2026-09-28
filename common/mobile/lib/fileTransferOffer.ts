export type FileOfferInput = {
  requestId: string;
  name: string;
  size: number;
  sha256: string;
  instruction: string;
  destinationPath: string;
};

export function transferIntent(instruction: string): 'upload' | 'edit' {
  return instruction.trim() ? 'edit' : 'upload';
}

export function buildFileOffer(input: FileOfferInput): Record<string, unknown> {
  const destinationPath = input.destinationPath.trim();
  return {
    type: 'file_offer',
    requestId: input.requestId,
    name: input.name,
    size: input.size,
    sha256: input.sha256,
    purpose: transferIntent(input.instruction),
    ...(destinationPath ? { destinationPath } : {}),
  };
}
