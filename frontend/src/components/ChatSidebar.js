import React from 'react';
import './ChatSidebar.css';

function ChatSidebar({ 
  chats, 
  selectedChat, 
  onSelectChat, 
  onNewChat, 
  onDeleteChat,
  activeTab,
  onTabChange,
  loading 
}) {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-title">Docs QA</h1>
        <button className="new-chat-btn" onClick={onNewChat} title="New Chat">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M10 4V16M4 10H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      <div className="sidebar-tabs">
        <button 
          className={`tab-btn ${activeTab === 'chats' ? 'active' : ''}`}
          onClick={() => onTabChange('chats')}
        >
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <path d="M2 10C2 5.58172 5.58172 2 10 2C14.4183 2 18 5.58172 18 10C18 14.4183 14.4183 18 10 18H2V10Z" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M6 9H14M6 12H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          Chats
        </button>
        <button 
          className={`tab-btn ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => onTabChange('files')}
        >
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
            <path d="M4 4C4 2.89543 4.89543 2 6 2H11L15 6V16C15 17.1046 14.1046 18 13 18H6C4.89543 18 4 17.1046 4 16V4Z" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M11 2V6H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Files
        </button>
      </div>

      {activeTab === 'chats' && (
        <div className="chat-list">
          {loading ? (
            <div className="loading-state">Loading chats...</div>
          ) : chats.length === 0 ? (
            <div className="empty-state">
              <p>No chats yet</p>
              <p className="empty-state-hint">Click + to start a new chat</p>
            </div>
          ) : (
            chats.map(chat => (
              <div
                key={chat.chat_id}
                className={`chat-item ${selectedChat?.chat_id === chat.chat_id ? 'active' : ''}`}
                onClick={() => onSelectChat(chat)}
              >
                <div className="chat-item-content">
                  <div className="chat-item-title">{chat.title}</div>
                  <div className="chat-item-date">{formatDate(chat.updated_at)}</div>
                </div>
                <button
                  className="delete-chat-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Delete this chat?')) {
                      onDeleteChat(chat.chat_id);
                    }
                  }}
                  title="Delete chat"
                >
                  <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                    <path d="M7 3H13M3 6H17M15 6L14.5 15C14.5 16.1046 13.6046 17 12.5 17H7.5C6.39543 17 5.5 16.1046 5.5 15L5 6M8 9V13M12 9V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default ChatSidebar;
