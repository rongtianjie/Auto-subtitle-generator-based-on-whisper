import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Task } from '@/types';

interface AppContextType {
  // 认证状态
  isAuthenticated: boolean;
  user: { id: string; username: string; email: string; role: string } | null;
  setUser: (user: AppContextType['user']) => void;
  logout: () => void;

  // 主题状态
  theme: 'light' | 'dark';
  toggleTheme: () => void;

  // 通知状态
  notification: { type: 'success' | 'error' | 'info'; message: string } | null;
  showNotification: (type: 'success' | 'error' | 'info', message: string) => void;
  clearNotification: () => void;

  // 任务列表状态
  recentTasks: Task[];
  setRecentTasks: (tasks: Task[]) => void;
  isLoadingTasks: boolean;
  setIsLoadingTasks: (loading: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

interface AppContextProviderProps {
  children: ReactNode;
}

export function AppContextProvider({ children }: AppContextProviderProps) {
  // 认证状态
  const [user, setUser] = useState<AppContextType['user'] | null>(() => {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    return token ? (JSON.parse(localStorage.getItem('user') || 'null') || null) : null;
  });

  // 主题状态 (从 localStorage 读取)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'light';
  });

  // 通知状态
  const [notification, setNotification] = useState<AppContextType['notification']>(null);

  // 任务列表状态
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);

  const handleSetUser = useCallback((newUser: AppContextType['user']) => {
    setUser(newUser);
    if (newUser) {
      localStorage.setItem('user', JSON.stringify(newUser));
    } else {
      localStorage.removeItem('user');
    }
  }, []);

  const handleLogout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
  }, []);

  const handleToggleTheme = useCallback(() => {
    setTheme((prev) => {
      const newTheme = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', newTheme);
      return newTheme;
    });
  }, []);

  const handleShowNotification = useCallback(
    (type: 'success' | 'error' | 'info', message: string) => {
      setNotification({ type, message });
      // 3 秒后自动关闭
      setTimeout(() => setNotification(null), 3000);
    },
    []
  );

  const value: AppContextType = {
    isAuthenticated: !!user,
    user,
    setUser: handleSetUser,
    logout: handleLogout,
    theme,
    toggleTheme: handleToggleTheme,
    notification,
    showNotification: handleShowNotification,
    clearNotification: () => setNotification(null),
    recentTasks,
    setRecentTasks,
    isLoadingTasks,
    setIsLoadingTasks,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within AppContextProvider');
  }
  return context;
}
