import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from './infrastructure/query/QueryClientProvider';
import Navbar from './presentation/components/layout/Navbar';
import { DeviceList, DeviceManagement, DevicePassport, CreatePolicyPage } from './presentation/pages';

/**
 * App - Componente principal de la aplicación
 */
function App(): JSX.Element {
  return (
    <QueryClientProvider>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
          <Navbar />
          <Routes>
            <Route path="/devices" element={<DeviceList />} />
            <Route path="/devices/:id" element={<DeviceManagement />} />
            <Route path="/devices/:id/passport" element={<DevicePassport />} />
            <Route path="/devices/:id/policies/create" element={<CreatePolicyPage />} />
            <Route path="*" element={<Navigate to="/devices" replace />} />
          </Routes>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;

