/**
 * Authentication context for the music app.
 * Manages user state, login, logout, and authentication tokens.
 */
'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import Cookies from 'js-cookie';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  profile_image_url?: string;
  bio?: string;
  created_at?: string;
  upload_count?: number;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateUser: (userData: Partial<User>) => void;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  bio?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  // Get stored tokens
  const getTokens = () => {
    const accessToken = Cookies.get('access_token');
    const refreshToken = Cookies.get('refresh_token');
    return { accessToken, refreshToken };
  };

  // Store tokens
  const storeTokens = (tokens: AuthTokens) => {
    Cookies.set('access_token', tokens.access_token, {
      expires: tokens.expires_in / (60 * 60 * 24), // Convert seconds to days
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict'
    });
    Cookies.set('refresh_token', tokens.refresh_token, {
      expires: 30, // 30 days
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict'
    });
  };

  // Clear tokens
  const clearTokens = () => {
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
  };

  // API call helper with auth
  const apiCall = async (endpoint: string, options: RequestInit = {}) => {
    const { accessToken } = getTokens();
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API request failed');
    }

    return response.json();
  };

  // Fetch current user info
  const fetchUser = async () => {
    try {
      const userData = await apiCall('/auth/me');
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      clearTokens();
      setUser(null);
    }
  };

  // Login function
  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true);
      const tokens = await apiCall('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      storeTokens(tokens);
      await fetchUser();
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Register function
  const register = async (userData: RegisterData) => {
    try {
      setIsLoading(true);
      const tokens = await apiCall('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData),
      });

      storeTokens(tokens);
      await fetchUser();
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    clearTokens();
    setUser(null);
  };

  // Refresh token function
  const refreshToken = async () => {
    try {
      const { refreshToken: storedRefreshToken } = getTokens();
      if (!storedRefreshToken) {
        throw new Error('No refresh token available');
      }

      const tokens = await apiCall('/auth/refresh', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${storedRefreshToken}`,
        },
      });

      storeTokens(tokens);
      await fetchUser();
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      throw error;
    }
  };

  // Update user function
  const updateUser = (userData: Partial<User>) => {
    if (user) {
      setUser({ ...user, ...userData });
    }
  };

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      const { accessToken } = getTokens();
      
      if (accessToken) {
        try {
          await fetchUser();
        } catch (error) {
          console.error('Auth initialization failed:', error);
          clearTokens();
        }
      }
      
      setIsLoading(false);
    };

    initAuth();
  }, []);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(async () => {
      try {
        await refreshToken();
      } catch (error) {
        console.error('Auto refresh failed:', error);
      }
    }, 25 * 60 * 1000); // Refresh every 25 minutes

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout,
    refreshToken,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
