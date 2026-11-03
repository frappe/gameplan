const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

test("suspension disconnects only the target room on the correct site", async () => {
  let receive;
  let onError;
  let subscriptions = 0;
  const disconnected = [];
  const context = {
    module: { exports: {} },
    console,
    require: () => ({
      get_redis_subscriber: () => ({
        on: (_event, handler) => {
          onError = handler;
        },
        connect: async () => {},
        subscribe: async (_channel, handler) => {
          subscriptions++;
          receive = handler;
        },
      }),
    }),
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, "../restrictions.js"), "utf8"),
    context,
  );
  const handlers = [];
  const socket = (site) => ({
    nsp: {
      name: `/${site}`,
      disconnectSockets: (force) =>
        disconnected.push({ site, room: "*", force }),
      in: (room) => ({
        disconnectSockets: (force) => disconnected.push({ site, room, force }),
      }),
    },
    on: (_event, handler) => handlers.push(handler),
  });
  context.module.exports(socket("alpha"));
  context.module.exports(socket("beta"));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(subscriptions, 1);
  receive(
    JSON.stringify({
      event: "gameplan:account_suspended",
      namespace: "alpha",
      message: { user: "member@example.test" },
    }),
  );
  assert.deepEqual(disconnected, [
    { site: "alpha", room: "user:member@example.test", force: true },
  ]);
  handlers[0]();
  receive(
    JSON.stringify({
      event: "gameplan:account_suspended",
      namespace: "alpha",
      message: { user: "member@example.test" },
    }),
  );
  assert.equal(disconnected.length, 1);
  onError();
  assert.deepEqual(disconnected[1], { site: "beta", room: "*", force: true });
});
