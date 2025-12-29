import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './ChatArea.css';

function ChatArea({ selectedChat, userId, apiUrl, onChatUpdate }) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (selectedChat?.messages) {
      setMessages(selectedChat.messages);
    } else {
      setMessages([]);
    }
  }, [selectedChat]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || !selectedChat || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);

    // Add user message to UI immediately
    const tempUserMessage = {
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMessage]);

    try {
      // Save user message to backend
      const userMsgResponse = await fetch(`${apiUrl}/chats/${selectedChat.chat_id}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          role: 'user',
          content: userMessage,
        }),
      });

      if (!userMsgResponse.ok) {
        throw new Error('Failed to save user message');
      }

      // Generate AI response
      const generateResponse = await fetch(`${apiUrl}/chat/generate-response`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: selectedChat.chat_id,
          user_id: userId,
          message: userMessage,
        }),
      });

      const responseData = await generateResponse.json();

      if (responseData.success) {
        // Add assistant message
        const tempAssistantMessage = {
          role: 'assistant',
          content: responseData.response,
          created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, tempAssistantMessage]);

        // Save assistant message to backend
        await fetch(`${apiUrl}/chats/${selectedChat.chat_id}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            role: 'assistant',
            content: responseData.response,
          }),
        });

        // Update chat in list (to update timestamp)
        const updatedChat = {
          ...selectedChat,
          updated_at: new Date().toISOString(),
        };
        onChatUpdate(updatedChat);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
        isError: true,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!selectedChat) {
    return (
      <div className="chat-area">
        <div className="empty-chat">
          <div className="empty-chat-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
              <path d="M8 9H16M8 13H14M6 18L3 21V6C3 4.89543 4.89543 4 6 4H18C19.1046 4 20 4.89543 20 6V15C20 16.1046 19.1046 17 18 17H9L6 18Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h2>Welcome to Docs QA</h2>
          <p>Select a chat from the sidebar or create a new one to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      <div className="chat-header">
        <h2>{selectedChat.title}</h2>
        <div className="chat-info">
          {messages.length} {messages.length === 1 ? 'message' : 'messages'}
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="no-messages">
            <p>No messages yet. Start the conversation!</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.role} ${message.isError ? 'error' : ''}`}
            >
              <div className="message-avatar">
                {message.role === 'user' ? (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M4 20C4 16.6863 6.68629 14 10 14H14C17.3137 14 20 16.6863 20 20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                ) : (
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                    <circle cx="9" cy="10" r="1" fill="currentColor"/>
                    <circle cx="15" cy="10" r="1" fill="currentColor"/>
                    <path d="M9 14C9.5 15 10.5 16 12 16C13.5 16 14.5 15 15 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
              </div>
              <div className="message-content">
                <div className="message-text">
                  {message.role === 'assistant' ? (
                    <ReactMarkdown
                      components={{
                        code({node, inline, className, children, ...props}) {
                          const match = /language-(\w+)/.exec(className || '');
                          return !inline && match ? (
                            <SyntaxHighlighter
                              style={vscDarkPlus}
                              language={match[1]}
                              PreTag="div"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          );
                        },
                        p({children}) {
                          return <p style={{ margin: '0.5em 0' }}>{children}</p>;
                        },
                        h1({children}) {
                          return <h1 style={{ fontSize: '1.5em', fontWeight: 'bold', margin: '0.5em 0' }}>{children}</h1>;
                        },
                        h2({children}) {
                          return <h2 style={{ fontSize: '1.3em', fontWeight: 'bold', margin: '0.5em 0' }}>{children}</h2>;
                        },
                        h3({children}) {
                          return <h3 style={{ fontSize: '1.1em', fontWeight: 'bold', margin: '0.5em 0' }}>{children}</h3>;
                        },
                        ul({children}) {
                          return <ul style={{ marginLeft: '1.5em', margin: '0.5em 0' }}>{children}</ul>;
                        },
                        ol({children}) {
                          return <ol style={{ marginLeft: '1.5em', margin: '0.5em 0' }}>{children}</ol>;
                        },
                        li({children}) {
                          return <li style={{ margin: '0.25em 0' }}>{children}</li>;
                        },
                        strong({children}) {
                          return <strong style={{ fontWeight: 'bold' }}>{children}</strong>;
                        },
                        em({children}) {
                          return <em style={{ fontStyle: 'italic' }}>{children}</em>;
                        },
                        blockquote({children}) {
                          return <blockquote style={{ borderLeft: '3px solid #ddd', paddingLeft: '1em', margin: '0.5em 0', color: '#666' }}>{children}</blockquote>;
                        }
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  ) : (
                    message.content
                  )}
                </div>
                <div className="message-time">{formatTime(message.created_at)}</div>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-avatar">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <rect x="4" y="4" width="16" height="16" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                <circle cx="9" cy="10" r="1" fill="currentColor"/>
                <circle cx="15" cy="10" r="1" fill="currentColor"/>
                <path d="M9 14C9.5 15 10.5 16 12 16C13.5 16 14.5 15 15 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="message-content">
              <div className="message-text">
                <span className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="message-input-container" onSubmit={sendMessage}>
        <input
          type="text"
          className="message-input"
          placeholder="Ask a question about your documents..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="send-button"
          disabled={!inputMessage.trim() || isLoading}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </form>
    </div>
  );
}

export default ChatArea;
