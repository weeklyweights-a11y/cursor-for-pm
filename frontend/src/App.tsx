import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/authContext";
import { PrivateRoute } from "./components/PrivateRoute";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { FeedbackPage } from "./pages/FeedbackPage";
import { FeedbackDetailPage } from "./pages/FeedbackDetailPage";
import { UploadPage } from "./pages/UploadPage";
import { AddManualFeedbackPage } from "./pages/AddManualFeedbackPage";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerDetailPage } from "./pages/CustomerDetailPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { SettingsPage } from "./pages/SettingsPage";
import { PrioritiesPage } from "./pages/PrioritiesPage";
import { ThemeDetailPage } from "./pages/ThemeDetailPage";
import { BriefPage } from "./pages/BriefPage";
import { SpecPage } from "./pages/SpecPage";
import { ThemeBriefPage } from "./pages/ThemeBriefPage";
import { ThemeSpecPage } from "./pages/ThemeSpecPage";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/onboarding" element={<PrivateRoute />}>
            <Route index element={<OnboardingPage />} />
          </Route>
          <Route path="/dashboard" element={<PrivateRoute />}>
            <Route index element={<DashboardPage />} />
          </Route>
          <Route path="/priorities" element={<PrivateRoute />}>
            <Route index element={<PrioritiesPage />} />
          </Route>
          <Route path="/themes/:id" element={<PrivateRoute />}>
            <Route index element={<ThemeDetailPage />} />
            <Route path="brief" element={<ThemeBriefPage />} />
            <Route path="spec" element={<ThemeSpecPage />} />
          </Route>
          <Route path="/briefs/:id" element={<PrivateRoute />}>
            <Route index element={<BriefPage />} />
          </Route>
          <Route path="/specs/:id" element={<PrivateRoute />}>
            <Route index element={<SpecPage />} />
          </Route>
          <Route path="/feedback" element={<PrivateRoute />}>
            <Route index element={<FeedbackPage />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="add-manual" element={<AddManualFeedbackPage />} />
            <Route path=":id" element={<FeedbackDetailPage />} />
          </Route>
          <Route path="/customers" element={<PrivateRoute />}>
            <Route index element={<CustomersPage />} />
            <Route path=":id" element={<CustomerDetailPage />} />
          </Route>
          <Route path="/review-queue" element={<PrivateRoute />}>
            <Route index element={<ReviewQueuePage />} />
          </Route>
          <Route path="/settings" element={<PrivateRoute />}>
            <Route index element={<SettingsPage />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
