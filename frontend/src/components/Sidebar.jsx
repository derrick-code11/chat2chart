function groupByDate(conversations) {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOf7DaysAgo = new Date(startOfToday);
  startOf7DaysAgo.setDate(startOf7DaysAgo.getDate() - 7);

  const groups = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Last 7 days", items: [] },
    { label: "Older", items: [] },
  ];

  for (const c of conversations) {
    const d = new Date(c.updated_at);
    if (d >= startOfToday) groups[0].items.push(c);
    else if (d >= startOfYesterday) groups[1].items.push(c);
    else if (d >= startOf7DaysAgo) groups[2].items.push(c);
    else groups[3].items.push(c);
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function Sidebar({
  user,
  conversations,
  activeConvId,
  onSelect,
  onNewChat,
  onSignOut,
}) {
  const groups = groupByDate(conversations);

  return (
    <aside
      style={{
        width: 240,
        minWidth: 240,
        backgroundColor: "#2A2A2A",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        borderRight: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* Logo */}
      <div style={{ padding: "20px 16px 14px" }}>
        <span
          style={{
            fontFamily: '"Geist Mono", monospace',
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "#C4D8CB",
          }}
        >
          chat2chart
        </span>
      </div>

      {/* New chat */}
      <div style={{ padding: "0 10px 10px" }}>
        <button
          onClick={onNewChat}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            gap: 7,
            padding: "7px 12px",
            backgroundColor: "transparent",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 4,
            color: "#D4D0CA",
            fontSize: 13,
            cursor: "pointer",
            fontFamily: "Inter, sans-serif",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path
              d="M6 1v10M1 6h10"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="square"
            />
          </svg>
          New chat
        </button>
      </div>

      {/* Conversation list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "4px 10px 0" }}>
        {conversations.length === 0 ? (
          <p
            style={{
              fontSize: 12,
              color: "#4A4A3A",
              padding: "8px 12px",
              fontFamily: "Inter, sans-serif",
            }}
          >
            No chats yet
          </p>
        ) : (
          groups.map(({ label, items }) => (
            <div key={label} style={{ marginBottom: 14 }}>
              <p
                style={{
                  fontSize: 10,
                  fontFamily: '"Geist Mono", monospace',
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  color: "#4A4A3A",
                  padding: "4px 12px 3px",
                }}
              >
                {label}
              </p>
              {items.map((c) => {
                const isActive = c.id === activeConvId;
                return (
                  <button
                    key={c.id}
                    onClick={() => onSelect(c.id)}
                    title={c.title || "Untitled chat"}
                    style={{
                      width: "100%",
                      display: "block",
                      textAlign: "left",
                      padding: "6px 12px",
                      borderRadius: 4,
                      border: "none",
                      cursor: "pointer",
                      backgroundColor: isActive ? "rgba(255,255,255,0.07)" : "transparent",
                      color: isActive ? "#E8E6E0" : "#7A7A6A",
                      fontSize: 13,
                      fontFamily: "Inter, sans-serif",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {c.title || "Untitled chat"}
                  </button>
                );
              })}
            </div>
          ))
        )}
      </div>

      {/* User section */}
      <div
        style={{
          padding: "10px",
          borderTop: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {user && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "4px 12px 8px",
            }}
          >
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.display_name}
                style={{ width: 24, height: 24, borderRadius: "50%", flexShrink: 0 }}
              />
            ) : (
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  backgroundColor: "#C4D8CB",
                  color: "#2A2A2A",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 11,
                  fontWeight: 600,
                  flexShrink: 0,
                }}
              >
                {(user.display_name ?? user.email)[0].toUpperCase()}
              </div>
            )}
            <span
              style={{
                fontSize: 12,
                color: "#7A7A6A",
                fontFamily: "Inter, sans-serif",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user.display_name ?? user.email}
            </span>
          </div>
        )}
        <button
          onClick={onSignOut}
          style={{
            width: "100%",
            padding: "6px 12px",
            backgroundColor: "transparent",
            border: "none",
            borderRadius: 4,
            color: "#4A4A3A",
            fontSize: 12,
            cursor: "pointer",
            textAlign: "left",
            fontFamily: "Inter, sans-serif",
          }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
