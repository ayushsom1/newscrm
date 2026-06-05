import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import RequireAuth from "@/components/RequireAuth";
import AppShell from "@/components/AppShell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Placeholder from "@/pages/Placeholder";
import AdvertiserList from "@/pages/advertisers/AdvertiserList";
import AdvertiserDetail from "@/pages/advertisers/AdvertiserDetail";
import AdvertiserForm from "@/pages/advertisers/AdvertiserForm";
import ClassifiedsList from "@/pages/classifieds/ClassifiedsList";
import ClassifiedNew from "@/pages/classifieds/ClassifiedNew";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <RequireAuth>
                <AppShell />
              </RequireAuth>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/advertisers" element={<AdvertiserList />} />
            <Route
              path="/advertisers/new"
              element={
                <RequireAuth roles={["ADMIN", "SALES"]}>
                  <AdvertiserForm />
                </RequireAuth>
              }
            />
            <Route path="/advertisers/:id" element={<AdvertiserDetail />} />
            <Route
              path="/advertisers/:id/edit"
              element={
                <RequireAuth roles={["ADMIN", "SALES"]}>
                  <AdvertiserForm />
                </RequireAuth>
              }
            />
            <Route path="/classifieds" element={<ClassifiedsList />} />
            <Route
              path="/classifieds/new"
              element={
                <RequireAuth roles={["ADMIN", "SALES", "ACCOUNTS"]}>
                  <ClassifiedNew />
                </RequireAuth>
              }
            />
            <Route path="/subscribers" element={<Placeholder title="Subscribers" sprint="Sprint 4" />} />
            <Route path="/complaints" element={<Placeholder title="Complaints" sprint="Sprint 5" />} />
            <Route path="/assistant" element={<Placeholder title="Assistant" sprint="Sprint 7" />} />
            <Route
              path="/settings"
              element={
                <RequireAuth roles={["ADMIN"]}>
                  <Placeholder title="Settings" sprint="Sprint 10" />
                </RequireAuth>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
