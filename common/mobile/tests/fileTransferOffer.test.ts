import { expect, test } from 'bun:test';
import { buildFileOffer, transferIntent } from '../lib/fileTransferOffer';

test('a mixed batch without instruction remains an upload', () => {
  expect(transferIntent('')).toBe('upload');
  expect(buildFileOffer({
    requestId: 'offer-1', name: 'notes.pdf', size: 12, sha256: 'a'.repeat(64),
    instruction: '', destinationPath: '/home/user/Projects',
  })).toEqual({
    type: 'file_offer', requestId: 'offer-1', name: 'notes.pdf', size: 12,
    sha256: 'a'.repeat(64), purpose: 'upload', destinationPath: '/home/user/Projects',
  });
});

test('an explicit edit instruction marks every file offer for an AiCut batch', () => {
  expect(transferIntent('  merge these videos  ')).toBe('edit');
  expect(buildFileOffer({
    requestId: 'offer-2', name: 'clip.mp4', size: 50, sha256: 'b'.repeat(64),
    instruction: 'trim from 1 to 3 seconds', destinationPath: ' ',
  })).toEqual({
    type: 'file_offer', requestId: 'offer-2', name: 'clip.mp4', size: 50,
    sha256: 'b'.repeat(64), purpose: 'edit',
  });
});
