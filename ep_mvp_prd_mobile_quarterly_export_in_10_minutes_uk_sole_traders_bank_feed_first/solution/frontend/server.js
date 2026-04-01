import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const frontendDir = normalize(join(__filename, ".."));
const portArg = process.argv[2];
const defaultPort = Number(portArg || process.env.EVIDENCE_UI_PORT || 4173);

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8"
};

function resolvePath(requestUrl) {
  const pathname = new URL(requestUrl, "http://127.0.0.1").pathname;
  const relativePath = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  return normalize(join(frontendDir, relativePath));
}

const server = createServer(async (req, res) => {
  try {
    const filePath = resolvePath(req.url || "/");

    if (!filePath.startsWith(frontendDir)) {
      res.writeHead(403).end("Forbidden");
      return;
    }

    const body = await readFile(filePath);
    const contentType = contentTypes[extname(filePath)] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": contentType });
    res.end(body);
  } catch (error) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(`Not found: ${error.message}`);
  }
});

server.listen(defaultPort, "127.0.0.1", () => {
  console.log(`Evidence UI ready at http://127.0.0.1:${defaultPort}`);
});
