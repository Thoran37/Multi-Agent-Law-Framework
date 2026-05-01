import { useState, useRef, useEffect } from 'react';
import { MessageCircle, Send, X, Minimize2, Maximize2 } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';
import '../styles/Chatbot.css';

function Chatbot({ caseId, isActive, currentStep, completedSteps = [], prediction, API }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      text: 'Hello! I\'m your Legal AI Tutor 🎓. Feel free to ask me any questions about the case. I\'ll explain everything in simple, student-friendly language!'
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Show chatbot after case is uploaded (based on completed steps which persist)
  const isCaseReady = isActive && caseId;
  
  // Enable chatbot once upload step is completed (steps that persist)
  const isFullyEnabled = isCaseReady && completedSteps && (
    completedSteps.includes('upload') || 
    completedSteps.includes('process') || 
    completedSteps.includes('predict') || 
    completedSteps.includes('simulate') || 
    completedSteps.includes('audit')
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputValue.trim()) {
      return;
    }

    // Add user message
    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      text: inputValue
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('question', inputValue);

      const response = await axios.post(
        `${API}/chatbot/${caseId}`,
        formData
      );

      const botMessage = {
        id: messages.length + 2,
        type: 'bot',
        text: response.data.answer
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = {
        id: messages.length + 2,
        type: 'bot',
        text: 'Sorry, I couldn\'t process your question. Please try again. Error: ' + (error.response?.data?.detail || error.message)
      };
      setMessages(prev => [...prev, errorMessage]);
      console.error('Chatbot error:', error);
    } finally {
      setLoading(false);
    }
  };

  // Don't show chatbot if not logged in (no case activity)
  if (!isCaseReady) {
    return null;
  }

  return (
    <div className="chatbot-container">
      {/* Chat Window */}
      <div className={`chatbot-window ${isOpen ? 'open' : 'closed'} ${isMinimized ? 'minimized' : ''}`}>
        {/* Header */}
        <div className={`chatbot-header ${!isFullyEnabled ? 'disabled' : ''}`}>
          <div className="chatbot-header-content">
            <MessageCircle size={20} className="chatbot-icon" />
            <h3>Legal AI Tutor</h3>
            {!isFullyEnabled && <span className="status-badge">Awaiting case upload</span>}
          </div>
          <div className="chatbot-controls">
            <button 
              onClick={() => setIsMinimized(!isMinimized)}
              className="chatbot-btn minimize-btn"
              title={isMinimized ? 'Expand' : 'Minimize'}
              disabled={!isFullyEnabled}
            >
              {isMinimized ? <Maximize2 size={16} /> : <Minimize2 size={16} />}
            </button>
            <button 
              onClick={() => setIsOpen(false)}
              className="chatbot-btn close-btn"
              title="Close"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Messages - only show if not minimized */}
        {!isMinimized && (
          <>
            <div className="chatbot-messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.type}-message`}>
                  <div className="message-content">
                    {msg.type === 'bot' && <span className="message-sender">🤖</span>}
                    {msg.type === 'user' && <span className="message-sender">👤</span>}
                    <p className="message-text">{msg.text}</p>
                  </div>
                </div>
              ))}
              {!isFullyEnabled && (
                <div className="message bot-message">
                  <div className="message-content">
                    <span className="message-sender">⏳</span>
                    <p className="message-text">Please upload a case and run the analysis to enable chat. Once simulation is complete, I'll be ready to answer your questions!</p>
                  </div>
                </div>
              )}
              {loading && (
                <div className="message bot-message">
                  <div className="message-content">
                    <span className="message-sender">🤖</span>
                    <p className="message-text">
                      <span className="typing-indicator">
                        <span></span><span></span><span></span>
                      </span>
                    </p>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <form onSubmit={handleSendMessage} className="chatbot-input-form">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={isFullyEnabled ? "Ask about the case..." : "Upload case to enable chat"}
                className="chatbot-input"
                disabled={loading || !isFullyEnabled}
              />
              <button 
                type="submit" 
                className="chatbot-send-btn"
                disabled={loading || !inputValue.trim() || !isFullyEnabled}
              >
                <Send size={18} />
              </button>
            </form>
          </>
        )}
      </div>

      {/* Floating Button - only show if chat is closed and case is ready */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className={`chatbot-fab ${!isFullyEnabled ? 'disabled' : ''}`}
          title={isFullyEnabled ? "Open Chat" : "Upload case to enable chat"}
        >
          <MessageCircle size={28} />
          <span className={`chatbot-badge ${!isFullyEnabled ? 'disabled' : ''}`}>{isFullyEnabled ? '?' : '!'}</span>
        </button>
      )}
    </div>
  );
}

export default Chatbot;
