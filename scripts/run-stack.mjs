#!/usr/bin/env node
import { existsSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import process from "node:process";

const mode = process.argv[2] ?? "dev";
const root = process.cwd();
const isWin = process.platform === "win32";
const frontendDir = path.join(root, "frontend");
const venvDir = path.join(root, ".venv");
const venvPython = isWin ? path.join(venvDir, "Scripts", "python.exe") : path.join(venvDir, "bin", "python");

function normalizeCommand(command) {
  if (!isWin) return command;
  if (command === "npm") return "npm.cmd";
  return command;
}

function runBlocking(command, args, cwd = root) {
  const res = spawnSync(normalizeCommand(command), args, { cwd, stdio: "inherit", shell: false });
  if (res.status !== 0) {
    process.exit(res.status ?? 1);
  }
}

function ensureDocker() {
  runBlocking("docker", ["compose", "up", "-d"]);
}

function ensureFrontendDeps() {
  if (!existsSync(path.join(frontendDir, "node_modules"))) {
    runBlocking("npm", ["install"], frontendDir);
  }
}

function ensureBackendVenvAndDeps() {
  if (!existsSync(venvPython)) {
    runBlocking(isWin ? "py" : "python3", ["-m", "venv", ".venv"]);
  }
  runBlocking(venvPython, ["-m", "pip", "install", "-r", "backend/requirements.txt"]);
}

function spawnManaged(name, command, args, cwd = root) {
  const child = spawn(normalizeCommand(command), args, {
    cwd,
    shell: false,
    stdio: "inherit",
    env: process.env,
  });
  child.on("exit", (code) => {
    if (code && code !== 0) {
      console.error(`[${name}] exited with code ${code}`);
      shutdown(1);
    }
  });
  return child;
}

const children = [];
function shutdown(code = 0) {
  for (const child of children) {
    if (!child.killed) child.kill("SIGTERM");
  }
  process.exit(code);
}

if (mode === "up") {
  ensureDocker();
  process.exit(0);
}

ensureDocker();
ensureFrontendDeps();
ensureBackendVenvAndDeps();

if (mode === "dev") {
  const c = spawnManaged("dev", venvPython, ["main.py"]);
  children.push(c);
} else if (mode === "prod") {
  runBlocking("npm", ["run", "build"], frontendDir);
  children.push(spawnManaged("api", venvPython, ["-m", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]));
  const celeryArgs = ["-m", "celery", "-A", "backend.celery_app", "worker", "--loglevel=info"];
  if (isWin) celeryArgs.push("--pool=solo", "--concurrency=1");
  children.push(spawnManaged("celery", venvPython, celeryArgs));
  children.push(spawnManaged("next", "npm", ["run", "start", "--prefix", "frontend"]));
} else {
  console.error(`Unknown mode: ${mode}`);
  process.exit(1);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));
