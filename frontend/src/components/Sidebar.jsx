import { groupByDate } from "../lib/dates";

export default function Sidebar({
  user,
  conversations,
  activeConvId,
  onSelect,
  onNewChat,
  onDelete,
  onSignOut,
}) {
  const groups = groupByDate(conversations);

  return (
    <aside className="w-60 min-w-60 bg-brand-dark flex flex-col h-full border-r border-white/6">
      <div className="px-4 pt-5 pb-3.5">
        <span className="font-mono text-[13px] font-medium tracking-[0.18em] uppercase text-brand-primary">
          chat2chart
        </span>
      </div>

      <div className="px-2.5 pb-2.5">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full flex items-center gap-[7px] px-3 py-[7px] bg-transparent border border-white/10 rounded text-sidebar-hover text-[13px]"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" />
          </svg>
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2.5 pt-1">
        {conversations.length === 0 ? (
          <p className="text-xs text-sidebar-text-dim px-3 py-2">No chats yet</p>
        ) : (
          groups.map(({ label, items }) => (
            <div key={label} className="mb-3.5">
              <p className="text-[10px] font-mono uppercase tracking-widest text-sidebar-text-dim px-3 pt-1 pb-[3px]">
                {label}
              </p>
              {items.map((c) => {
                const isActive = c.id === activeConvId;
                return (
                  <div
                    key={c.id}
                    className={`group flex items-center rounded ${
                      isActive ? "bg-white/[0.07]" : "hover:bg-white/3"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => onSelect(c.id)}
                      title={c.title || "Untitled chat"}
                      className={`flex-1 min-w-0 block text-left px-3 py-1.5 rounded border-none bg-transparent text-[13px] truncate ${
                        isActive ? "text-sidebar-text-active" : "text-sidebar-text"
                      }`}
                    >
                      {c.title || "Untitled chat"}
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm("Delete this conversation?")) onDelete(c.id);
                      }}
                      title="Delete conversation"
                      className="shrink-0 hidden group-hover:flex items-center justify-center w-[26px] h-[26px] mr-1 border-none rounded bg-transparent text-sidebar-text hover:text-brand-error"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                        <path d="M10 11v6" />
                        <path d="M14 11v6" />
                        <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>

      <div className="p-2.5 border-t border-white/6">
        {user && (
          <div className="flex items-center gap-2 px-3 pt-1 pb-2">
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.display_name}
                className="w-6 h-6 rounded-full shrink-0"
              />
            ) : (
              <div className="w-6 h-6 rounded-full bg-brand-primary text-brand-dark flex items-center justify-center text-[11px] font-semibold shrink-0">
                {(user.display_name ?? user.email)[0].toUpperCase()}
              </div>
            )}
            <span className="text-xs text-sidebar-text truncate">
              {user.display_name ?? user.email}
            </span>
          </div>
        )}
        <button
          type="button"
          onClick={onSignOut}
          className="w-full flex items-center gap-[7px] px-3 py-[7px] bg-transparent border border-white/8 rounded text-muted-light text-xs text-left transition-colors duration-150 hover:bg-white/5 hover:text-sidebar-hover"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Sign out
        </button>
      </div>
    </aside>
  );
}
