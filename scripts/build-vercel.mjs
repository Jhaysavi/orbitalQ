import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const output = "dist/index.html";
const packaged = readFileSync(output, "utf8");
if (packaged.includes('type="application/json">[{')) {
    console.log("Using packaged SPHEREx observations.");
    process.exit(0);
}

function run(command, args, timeout) {
    const result = spawnSync(command, args, { stdio: "inherit", timeout });
    if (result.error) throw result.error;
    if (result.status !== 0) {
        throw new Error(command + " exited with " + (result.signal ?? result.status));
    }
}

try {
    const python = ["python3.12", "python3"].find(command =>
        spawnSync(command, ["-c", "import sys; sys.exit(sys.version_info < (3, 11))"]).status === 0
    );
    if (!python) throw new Error("Python 3.11+ is unavailable in the build environment.");
    const env = join(tmpdir(), "orbitalq-venv");
    run(python, ["-m", "venv", env], 60_000);
    const interpreter = join(env, "bin", "python");
    run(interpreter, ["-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements-viewer.txt"], 180_000);
    run(interpreter, [
        "validate_spherex.py", "--target", "Barnard", "--ra", "269.4515", "--dec", "4.769",
        "--bandpass", "SPHEREx-D1", "--size", "0.08", "--max-downloads", "6",
    ], 240_000);
    run(interpreter, ["build_viewer.py", "--barnard", "data/inventory/Barnard_manifest.json", "--output", output], 120_000);
    console.log("Built the Barnard comparison from NASA/IPAC IRSA observations.");
} catch (error) {
    console.warn("SPHEREx comparison unavailable. Publishing the archive and reproduction links.");
    console.warn(error.message);
}
