// Frappe loads app handlers after authentication. Keep doc_subscribe unchanged;
// doc_open joins the separate presence room, whose payload contains account emails.
module.exports = function (socket) {
  // System-type Guests must not receive the Desk-wide list_update feed either.
  socket.leave("all");
  const canViewPresence = async () => {
    const response = await socket.frappe_request(
      "/api/method/gameplan.guest_payload.can_view_presence",
    );
    const { message } = await response.json();
    return response.ok && message === true;
  };
  canViewPresence()
    .then((allowed) => {
      if (allowed && socket.user_type === "System User") socket.join("all");
    })
    .catch(() => {});
  socket.use(async ([event], next) => {
    if (event !== "doc_open") return next();
    try {
      if (await canViewPresence()) return next();
    } catch {
      // A failed identity check must not admit the socket to the presence room.
    }
    next(new Error("Document presence is not available to Guests"));
  });
};
