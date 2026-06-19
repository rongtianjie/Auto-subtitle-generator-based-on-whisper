import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/hooks/useAuth';
import { BackendHealthProvider } from '@/hooks/useBackendHealth';
import { AppContextProvider } from '@/context/AppContext';
import { HealthMonitor } from '@/components/shared/HealthMonitor';
import { Layout } from '@/components/layout/Layout';
import { AdminLayout } from '@/components/layout/AdminLayout';
import { Loader2 } from 'lucide-react';

import Home from '@/pages/Home';
import TaskDetail from '@/pages/TaskDetail';
import AdminSetup from '@/pages/AdminSetup';

// 管理后台页面懒加载
const Overview = lazy(() => import('@/pages/admin/Overview'));
const SystemConfig = lazy(() => import('@/pages/admin/SystemConfig'));
const ModelManagement = lazy(() => import('@/pages/admin/ModelManagement'));
const LlmConfig = lazy(() => import('@/pages/admin/LlmConfig'));
const LogViewer = lazy(() => import('@/pages/admin/LogViewer'));
const UserManagement = lazy(() => import('@/pages/admin/UserManagement'));
const FileManagement = lazy(() => import('@/pages/admin/FileManagement'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <BackendHealthProvider>
        <AuthProvider>
          <AppContextProvider>
            <HealthMonitor />
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route element={<Layout />}>
                  <Route path="/" element={<Home />} />
                  <Route path="/tasks/:id" element={<TaskDetail />} />
                  <Route path="/admin/setup" element={<AdminSetup />} />

                  {/* Redirects for removed pages */}
                  <Route path="/login" element={<Navigate to="/" replace />} />
                  <Route path="/register" element={<Navigate to="/" replace />} />
                  <Route path="/dashboard" element={<Navigate to="/#recent" replace />} />
                </Route>

                {/* Admin routes with sidebar layout */}
                <Route path="/admin" element={<AdminLayout />}>
                  <Route index element={<Overview />} />
                  <Route path="config" element={<SystemConfig />} />
                  <Route path="models" element={<ModelManagement />} />
                  <Route path="llm" element={<LlmConfig />} />
                  <Route path="logs" element={<LogViewer />} />
                  <Route path="users" element={<UserManagement />} />
                  <Route path="files" element={<FileManagement />} />
                </Route>
              </Routes>
            </Suspense>
          </AppContextProvider>
        </AuthProvider>
      </BackendHealthProvider>
    </BrowserRouter>
  );
}

export default App;
