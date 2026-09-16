// Let Vite's native workers close naturally on Windows instead of calling
// process.exit while a libuv async handle is already being closed.
if (process.platform === 'win32') {
  const immediateExit = process.exit.bind(process);
  process.exit = function gracefulBuildExit(code = 0) {
    if (Number(code) !== 0) return immediateExit(code);
    process.exitCode = 0;
  };
}
