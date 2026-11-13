import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

test("homepage renders without secrets",async()=>{
  const response=await worker.fetch(new Request("https://example.workers.dev/"),{});
  assert.equal(response.status,200);
  assert.match(await response.text(),/電玩喵/);
});
test("API refuses requests if admin secret is missing",async()=>{
  const response=await worker.fetch(new Request("https://example.workers.dev/api/health"),{PUBLISHER:{}});
  assert.equal(response.status,503);
});
test("API refuses anonymous requests with configured secret",async()=>{
  const response=await worker.fetch(new Request("https://example.workers.dev/api/health"),{ADMIN_API_TOKEN:"x".repeat(40),PUBLISHER:{}});
  assert.equal(response.status,401);
});
