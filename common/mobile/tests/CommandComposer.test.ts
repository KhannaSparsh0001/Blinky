import { expect, test } from 'bun:test';

// The composer case mocks React hooks; run it in a separate Bun process so
// those module mocks cannot replace the WebSocket hook suite's React mock.
test('composer exposes the PC transfer action', () => {
  const run = Bun.spawnSync({
    cmd: [process.execPath, 'test', './common/mobile/tests/CommandComposer.case.tsx'],
    cwd: process.cwd(),
    stdout: 'pipe',
    stderr: 'pipe',
  });
  const output = `${new TextDecoder().decode(run.stdout)}\n${new TextDecoder().decode(run.stderr)}`;
  expect(run.exitCode, output).toBe(0);
});
