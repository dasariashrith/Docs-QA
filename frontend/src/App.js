import React, { useState, useEffect } from 'react';
import './App.css';
import ChatSidebar from './components/ChatSidebar';
import ChatArea from './components/ChatArea';
import FilesTab from './components/FilesTab';

const API_URL = 'http://localhost:5000';
const USER_ID = 'user_123';

function App() {
  const [activeTab, setActiveTab] = useState('chats');
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(false);

  // Fetch user's chats on mount
  useEffect(() => {
    fetchChats();
  }, []);

  const fetchChats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/chats?user_id=${USER_ID}`);
      const data = await response.json();
      if (data.success) {
        setChats(data.chats);
      }
    } catch (error) {
      console.error('Error fetching chats:', error);
    } finally {
      setLoading(false);
    }
  };

  const createNewChat = async () => {
    try {
      const response = await fetch(`${API_URL}/chats`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: USER_ID,
          title: 'New Chat',
        }),
      });
      const data = await response.json();
      if (data.success) {
        setChats([data.chat, ...chats]);
        setSelectedChat(data.chat);
        setActiveTab('chats');
      }
    } catch (error) {
      console.error('Error creating chat:', error);
    }
  };

  const deleteChat = async (chatId) => {
    try {
      const response = await fetch(`${API_URL}/chats/${chatId}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      if (data.success) {
        setChats(chats.filter(chat => chat.chat_id !== chatId));
        if (selectedChat?.chat_id === chatId) {
          setSelectedChat(null);
        }
      }
    } catch (error) {
      console.error('Error deleting chat:', error);
    }
  };

  const selectChat = async (chat) => {
    try {
      const response = await fetch(`${API_URL}/chats/${chat.chat_id}?include_messages=true`);
      const data = await response.json();
      if (data.success) {
        setSelectedChat(data.chat);
        setActiveTab('chats');
      }
    } catch (error) {
      console.error('Error fetching chat:', error);
    }
  };

  const updateChatInList = (updatedChat) => {
    setChats(chats.map(chat => 
      chat.chat_id === updatedChat.chat_id ? updatedChat : chat
    ));
  };

  return (
    <div className="app-container">
      <ChatSidebar
        chats={chats}
        selectedChat={selectedChat}
        onSelectChat={selectChat}
        onNewChat={createNewChat}
        onDeleteChat={deleteChat}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        loading={loading}
      />
      <div className="main-content">
        {activeTab === 'chats' ? (
          <ChatArea
            selectedChat={selectedChat}
            userId={USER_ID}
            apiUrl={API_URL}
            onChatUpdate={updateChatInList}
          />
        ) : (
          <FilesTab
            userId={USER_ID}
            apiUrl={API_URL}
          />
        )}
      </div>
    </div>
  );
}

export default App;
