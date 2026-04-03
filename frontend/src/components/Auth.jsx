import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { LogIn, UserPlus } from 'lucide-react';
import '../styles/Auth.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export function Auth({ onLoginSuccess }) {
  const [isSignup, setIsSignup] = useState(false);
  const [loading, setLoading] = useState(false);

  // Signup form
  const [signupForm, setSignupForm] = useState({
    name: '',
    age: '',
    roll_number: '',
    password: '',
    confirmPassword: ''
  });

  // Login form
  const [loginForm, setLoginForm] = useState({
    roll_number: '',
    password: ''
  });

  const handleSignupChange = (e) => {
    const { name, value } = e.target;
    setSignupForm(prev => ({ ...prev, [name]: value }));
  };

  const handleLoginChange = (e) => {
    const { name, value } = e.target;
    setLoginForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    
    // Validate form
    if (!signupForm.name || !signupForm.age || !signupForm.roll_number || !signupForm.password || !signupForm.confirmPassword) {
      toast.error('Please fill in all fields');
      return;
    }

    if (signupForm.password !== signupForm.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (isNaN(signupForm.age) || signupForm.age < 18) {
      toast.error('Age must be 18 or above');
      return;
    }

    if (!/^22071A\d{4}$/.test(signupForm.roll_number)) {
      toast.error('Invalid roll number. Format: 22071A followed by 4 digits (e.g., 22071A3259)');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/signup`, {
        name: signupForm.name,
        age: parseInt(signupForm.age),
        roll_number: signupForm.roll_number,
        password: signupForm.password
      });

      toast.success(response.data.message);
      setSignupForm({ name: '', age: '', roll_number: '', password: '', confirmPassword: '' });
      setIsSignup(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();

    if (!loginForm.roll_number || !loginForm.password) {
      toast.error('Please enter roll number and password');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, {
        roll_number: loginForm.roll_number,
        password: loginForm.password
      });

      if (response.data.success) {
        toast.success(response.data.message);
        // Pass user info to parent and switch to main app
        onLoginSuccess(response.data.user);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <div className="auth-header">
          <h1>Legal Multi-Agent Courtroom</h1>
          <p>AI-Powered Case Analysis & Simulation System</p>
        </div>

        {!isSignup ? (
          // Login Form
          <form onSubmit={handleLogin} className="auth-form">
            <h2>Student Login</h2>
            
            <div className="form-group">
              <label htmlFor="login-roll">Roll Number</label>
              <input
                id="login-roll"
                type="text"
                name="roll_number"
                placeholder="22071A3259"
                value={loginForm.roll_number}
                onChange={handleLoginChange}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-pass">Password</label>
              <input
                id="login-pass"
                type="password"
                name="password"
                placeholder="Enter your password"
                value={loginForm.password}
                onChange={handleLoginChange}
                disabled={loading}
              />
            </div>

            <button type="submit" className="btn-auth-primary" disabled={loading}>
              {loading ? <span className="loading-spinner"></span> : <LogIn size={20} />}
              Login
            </button>

            <div className="auth-toggle">
              <p>Don't have an account? <button type="button" onClick={() => setIsSignup(true)} className="toggle-btn">Sign up</button></p>
            </div>
          </form>
        ) : (
          // Signup Form
          <form onSubmit={handleSignup} className="auth-form">
            <h2>Create Student Account</h2>

            <div className="form-group">
              <label htmlFor="signup-name">Full Name</label>
              <input
                id="signup-name"
                type="text"
                name="name"
                placeholder="John Doe"
                value={signupForm.name}
                onChange={handleSignupChange}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="signup-age">Age</label>
              <input
                id="signup-age"
                type="number"
                name="age"
                placeholder="20"
                value={signupForm.age}
                onChange={handleSignupChange}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="signup-roll">Roll Number</label>
              <input
                id="signup-roll"
                type="text"
                name="roll_number"
                placeholder="22071A3259"
                value={signupForm.roll_number}
                onChange={handleSignupChange}
                disabled={loading}
              />
              <small>Format: 22071A followed by 4 digits</small>
            </div>

            <div className="form-group">
              <label htmlFor="signup-pass">Password</label>
              <input
                id="signup-pass"
                type="password"
                name="password"
                placeholder="Create a password"
                value={signupForm.password}
                onChange={handleSignupChange}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="signup-confirm">Confirm Password</label>
              <input
                id="signup-confirm"
                type="password"
                name="confirmPassword"
                placeholder="Confirm password"
                value={signupForm.confirmPassword}
                onChange={handleSignupChange}
                disabled={loading}
              />
            </div>

            <button type="submit" className="btn-auth-primary" disabled={loading}>
              {loading ? <span className="loading-spinner"></span> : <UserPlus size={20} />}
              Sign Up
            </button>

            <div className="auth-toggle">
              <p>Already have an account? <button type="button" onClick={() => setIsSignup(false)} className="toggle-btn">Login</button></p>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default Auth;
