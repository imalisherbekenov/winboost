import http from "node:http";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../out/", import.meta.url));
const types = {".html":"text/html; charset=utf-8", ".css":"text/css", ".js":"text/javascript", ".json":"application/json", ".txt":"text/plain; charset=utf-8", ".xml":"application/xml", ".svg":"image/svg+xml", ".png":"image/png", ".ico":"image/x-icon", ".exe":"application/octet-stream"};
const server = http.createServer(async (req, res) => {
  if (!["GET", "HEAD"].includes(req.method)) {res.writeHead(405, {Allow:"GET, HEAD"});res.end();return;}
  let pathname;
  try {pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);} catch {res.writeHead(400);res.end();return;}
  if (pathname.includes("\0")) {res.writeHead(400);res.end();return;}
  let file = path.resolve(root, "." + pathname);
  const relative = path.relative(root, file);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {res.writeHead(403);res.end();return;}
  let status = 200;
  try {
    if ((await stat(file)).isDirectory()) file = path.join(file, "index.html");
    if (!(await stat(file)).isFile()) throw new Error("Not a file");
  } catch {file = path.join(root, "404.html");status = 404;}
  try {
    const info = await stat(file);
    res.writeHead(status, {"Content-Type":types[path.extname(file)] || "application/octet-stream", "Content-Length":info.size, "X-Content-Type-Options":"nosniff"});
    if (req.method === "HEAD") {res.end();return;}
    const stream = createReadStream(file);
    stream.on("error", () => res.destroy());
    stream.pipe(res);
  } catch {res.writeHead(503);res.end("Run npm run build first.");}
});
server.listen(Number(process.env.PORT || 4173), "127.0.0.1", () => console.log(`WinBoost: http://127.0.0.1:${server.address().port}`));
