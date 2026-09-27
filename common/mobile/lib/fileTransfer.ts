import { File } from 'expo-file-system';

export interface MobileAttachment {
  uri: string;
  name: string;
  size?: number; // size in MB
  type: 'image' | 'video' | 'document';
  mimeType?: string;
  base64?: string;
}

/**
 * Converts an ArrayBuffer to a standard base64 string safely without stack overflow.
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunkSize = 8192;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode.apply(null, chunk as any);
  }
  return btoa(binary);
}

/**
 * Reads a local file URI (e.g. from DocumentPicker or ImagePicker) into a base64 string.
 */
export async function readUriAsBase64(uri: string): Promise<string> {
  try {
    const file = new File(uri);
    const buffer = await file.arrayBuffer();
    return arrayBufferToBase64(buffer);
  } catch (_fileErr) {
    // Fallback using standard React Native fetch + blob + FileReader
    const response = await fetch(uri);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        const b64 = result.includes(',') ? result.split(',')[1] : result;
        resolve(b64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
}
