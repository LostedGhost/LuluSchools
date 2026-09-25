import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./layout/AppLayout";
import { EleveProfileProvider } from "./eleve/EleveProfileContext";

import { LoginPage } from "./pages/LoginPage";
import { SignupTuteurPage } from "./pages/SignupTuteurPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { DashboardRedirect } from "./pages/DashboardRedirect";

import { TuteurDashboard } from "./pages/tuteur/TuteurDashboard";
import { NouvelleInscriptionPage } from "./pages/tuteur/NouvelleInscriptionPage";

import { EleveDashboard } from "./pages/eleve/EleveDashboard";
import { CoursListPage } from "./pages/eleve/CoursListPage";
import { QuizPage } from "./pages/eleve/QuizPage";
import { DevoirsListPage } from "./pages/eleve/DevoirsListPage";
import { DevoirDetailPage } from "./pages/eleve/DevoirDetailPage";
import { BulletinPage } from "./pages/eleve/BulletinPage";
import { ActesPage } from "./pages/eleve/ActesPage";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppLayout>
          <Routes>
            <Route path="/connexion" element={<LoginPage />} />
            <Route path="/inscription-tuteur" element={<SignupTuteurPage />} />
            <Route
              path="/changer-mot-de-passe"
              element={
                <RequireAuth>
                  <ChangePasswordPage />
                </RequireAuth>
              }
            />
            <Route path="/" element={<DashboardRedirect />} />

            <Route
              path="/tuteur"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <TuteurDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/nouvelle-inscription"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <NouvelleInscriptionPage />
                </RequireAuth>
              }
            />

            <Route
              path="/eleve"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <EleveDashboard />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/cours"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <CoursListPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/quiz/:quizId"
              element={
                <RequireAuth roles={["eleve"]}>
                  <QuizPage />
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/devoirs"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <DevoirsListPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/devoirs/:devoirId"
              element={
                <RequireAuth roles={["eleve"]}>
                  <DevoirDetailPage />
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/bulletin"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <BulletinPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/actes"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <ActesPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
          </Routes>
        </AppLayout>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
