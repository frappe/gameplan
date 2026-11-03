const { get_redis_subscriber } = require("../../frappe/node_utils");

const namespaces = new Map();
let subscription;

module.exports = function registerSuspensionDisconnect(socket) {
  if (!subscription) {
    const subscriber = get_redis_subscriber();
    const disconnectAll = () => {
      for (const { namespace } of namespaces.values())
        namespace.disconnectSockets(true);
    };
    // A lost suspension event must not leave an authenticated socket receiving content.
    subscriber.on("error", disconnectAll);
    subscription = subscriber.connect().then(() =>
      subscriber.subscribe("events", (raw) => {
        const message = JSON.parse(raw);
        if (message.event === "gameplan:account_suspended") {
          namespaces
            .get(message.namespace)
            ?.namespace.in(`user:${message.message.user}`)
            .disconnectSockets(true);
        }
      }),
    );
    subscription.catch((error) => {
      console.error("Suspension disconnect subscription failed", error);
      disconnectAll();
    });
  }
  const site = socket.nsp.name.slice(1);
  const entry = namespaces.get(site) || { namespace: socket.nsp, count: 0 };
  entry.count += 1;
  namespaces.set(site, entry);
  socket.on("disconnect", () => {
    entry.count -= 1;
    if (!entry.count) namespaces.delete(site);
  });
};
