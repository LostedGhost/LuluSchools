import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ConfirmationProvider } from "./components/Modale";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { RedirectIfAuthenticated } from "./auth/RedirectIfAuthenticated";
import { AppLayout, ThemeProvider } from "./layout/AppLayout";
import { EleveProfileProvider } from "./eleve/EleveProfileContext";
import { AdminEtabProvider } from "./admin/AdminEtabContext";
import { AccessibiliteProvider } from "./accessibilite/AccessibiliteContext";

import { LandingPage } from "./pages/LandingPage";

// Toutes les autres pages sont chargées à la demande (Lot 7.5, connectivité limitée) :
// un visiteur ne télécharge que le code des écrans qu’il ouvre réellement.
const ATraiterPage = lazy(() => import("./pages/admin/ATraiterPage").then((m) => ({ default: m.ATraiterPage })));
const ATraiterEtablissementPage = lazy(() => import("./pages/admin/ATraiterEtablissementPage").then((m) => ({ default: m.ATraiterEtablissementPage })));
const EtablissementsAnnuairePage = lazy(() => import("./pages/EtablissementsAnnuairePage").then((m) => ({ default: m.EtablissementsAnnuairePage })));
// Chargée à la demande : Leaflet + react-leaflet ne doivent jamais alourdir le
// bundle des autres pages (même principe que StarfieldScene, voir LandingPage.tsx).
const CartesPage = lazy(() => import("./pages/CartesPage").then((m) => ({ default: m.CartesPage })));
const LoginPage = lazy(() => import("./pages/LoginPage").then((m) => ({ default: m.LoginPage })));
const SignupPage = lazy(() => import("./pages/SignupPage").then((m) => ({ default: m.SignupPage })));
const ChangePasswordPage = lazy(() => import("./pages/ChangePasswordPage").then((m) => ({ default: m.ChangePasswordPage })));
const MotDePasseOubliePage = lazy(() => import("./pages/MotDePasseOubliePage").then((m) => ({ default: m.MotDePasseOubliePage })));
const DashboardRedirect = lazy(() => import("./pages/DashboardRedirect").then((m) => ({ default: m.DashboardRedirect })));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })));

const TuteurDashboard = lazy(() => import("./pages/tuteur/TuteurDashboard").then((m) => ({ default: m.TuteurDashboard })));
const NouvelleInscriptionPage = lazy(() => import("./pages/tuteur/NouvelleInscriptionPage").then((m) => ({ default: m.NouvelleInscriptionPage })));
const TuteurServicesScolairesPage = lazy(() => import("./pages/tuteur/ServicesScolairesPage").then((m) => ({ default: m.ServicesScolairesPage })));
const VieScolaireEnfantPage = lazy(() => import("./pages/tuteur/VieScolaireEnfantPage").then((m) => ({ default: m.VieScolaireEnfantPage })));
const DevoirsEnfantPage = lazy(() => import("./pages/tuteur/DevoirsEnfantPage").then((m) => ({ default: m.DevoirsEnfantPage })));
const MarketplaceEnfantPage = lazy(() => import("./pages/tuteur/MarketplaceEnfantPage").then((m) => ({ default: m.MarketplaceEnfantPage })));
const SessionsLiveEnfantPage = lazy(() => import("./pages/tuteur/SessionsLiveEnfantPage").then((m) => ({ default: m.SessionsLiveEnfantPage })));
const ElProfessorTuteurPage = lazy(() => import("./pages/tuteur/ElProfessorTuteurPage").then((m) => ({ default: m.ElProfessorTuteurPage })));
const CoffreFortPage = lazy(() => import("./pages/tuteur/CoffreFortPage").then((m) => ({ default: m.CoffreFortPage })));
const RadarFamilialPage = lazy(() => import("./pages/tuteur/RadarFamilialPage").then((m) => ({ default: m.RadarFamilialPage })));
const AlphabetisationPage = lazy(() => import("./pages/tuteur/AlphabetisationPage").then((m) => ({ default: m.AlphabetisationPage })));
const PasseportEnfantPage = lazy(() => import("./pages/tuteur/PasseportEnfantPage").then((m) => ({ default: m.PasseportEnfantPage })));

const EleveDashboard = lazy(() => import("./pages/eleve/EleveDashboard").then((m) => ({ default: m.EleveDashboard })));
const CoursListPage = lazy(() => import("./pages/eleve/CoursListPage").then((m) => ({ default: m.CoursListPage })));
const CoursDetailPage = lazy(() => import("./pages/eleve/CoursDetailPage").then((m) => ({ default: m.CoursDetailPage })));
const QuizPage = lazy(() => import("./pages/eleve/QuizPage").then((m) => ({ default: m.QuizPage })));
const DevoirsListPage = lazy(() => import("./pages/eleve/DevoirsListPage").then((m) => ({ default: m.DevoirsListPage })));
const DevoirDetailPage = lazy(() => import("./pages/eleve/DevoirDetailPage").then((m) => ({ default: m.DevoirDetailPage })));
const BulletinPage = lazy(() => import("./pages/eleve/BulletinPage").then((m) => ({ default: m.BulletinPage })));
const ActesPage = lazy(() => import("./pages/eleve/ActesPage").then((m) => ({ default: m.ActesPage })));
const CoursDirectPage = lazy(() => import("./pages/eleve/CoursDirectPage").then((m) => ({ default: m.CoursDirectPage })));
const EleveServicesScolairesPage = lazy(() => import("./pages/eleve/ServicesScolairesPage").then((m) => ({ default: m.ServicesScolairesPage })));
const ElProfessorElevePage = lazy(() => import("./pages/eleve/ElProfessorElevePage").then((m) => ({ default: m.ElProfessorElevePage })));
const PasseportPage = lazy(() => import("./pages/eleve/PasseportPage").then((m) => ({ default: m.PasseportPage })));

const EnseignantDashboard = lazy(() => import("./pages/enseignant/EnseignantDashboard").then((m) => ({ default: m.EnseignantDashboard })));
const PostesListPage = lazy(() => import("./pages/enseignant/PostesListPage").then((m) => ({ default: m.PostesListPage })));
const PostulerPage = lazy(() => import("./pages/enseignant/PostulerPage").then((m) => ({ default: m.PostulerPage })));
const MesCandidaturesPage = lazy(() => import("./pages/enseignant/MesCandidaturesPage").then((m) => ({ default: m.MesCandidaturesPage })));
const MesContratsPage = lazy(() => import("./pages/enseignant/MesContratsPage").then((m) => ({ default: m.MesContratsPage })));
const MesCoursPage = lazy(() => import("./pages/enseignant/MesCoursPage").then((m) => ({ default: m.MesCoursPage })));
const MesDevoirsPage = lazy(() => import("./pages/enseignant/MesDevoirsPage").then((m) => ({ default: m.MesDevoirsPage })));
const SessionsLivePage = lazy(() => import("./pages/enseignant/SessionsLivePage").then((m) => ({ default: m.SessionsLivePage })));
const MesSallesPage = lazy(() => import("./pages/enseignant/MesSallesPage").then((m) => ({ default: m.MesSallesPage })));
const ElProfessorPage = lazy(() => import("./pages/enseignant/ElProfessorPage").then((m) => ({ default: m.ElProfessorPage })));
const SalleLivePage = lazy(() => import("./pages/cours_direct/SalleLivePage").then((m) => ({ default: m.SalleLivePage })));

const AdminEtabDashboard = lazy(() => import("./pages/admin_etablissement/AdminEtabDashboard").then((m) => ({ default: m.AdminEtabDashboard })));
const ClassesPage = lazy(() => import("./pages/admin_etablissement/ClassesPage").then((m) => ({ default: m.ClassesPage })));
const ConsoleEtablissementPage = lazy(() => import("./pages/admin_etablissement/ConsoleEtablissementPage").then((m) => ({ default: m.ConsoleEtablissementPage })));
const RentreePage = lazy(() => import("./pages/admin_etablissement/RentreePage").then((m) => ({ default: m.RentreePage })));
const VieScolairePage = lazy(() => import("./pages/admin_etablissement/VieScolairePage").then((m) => ({ default: m.VieScolairePage })));
const InscriptionsAValiderPage = lazy(() => import("./pages/admin_etablissement/InscriptionsAValiderPage").then((m) => ({ default: m.InscriptionsAValiderPage })));
const RecrutementPage = lazy(() => import("./pages/admin_etablissement/RecrutementPage").then((m) => ({ default: m.RecrutementPage })));
const ContestationsPage = lazy(() => import("./pages/admin_etablissement/ContestationsPage").then((m) => ({ default: m.ContestationsPage })));
const ActesAdminPage = lazy(() => import("./pages/admin_etablissement/ActesAdminPage").then((m) => ({ default: m.ActesAdminPage })));
const ReferentielsEtabPage = lazy(() => import("./pages/admin_etablissement/ReferentielsEtabPage").then((m) => ({ default: m.ReferentielsEtabPage })));
const SaisiePapierPage = lazy(() => import("./pages/admin_etablissement/SaisiePapierPage").then((m) => ({ default: m.SaisiePapierPage })));
const BulletinsEnfantPage = lazy(() => import("./pages/tuteur/BulletinsEnfantPage").then((m) => ({ default: m.BulletinsEnfantPage })));
const ServicesScolairesAdminPage = lazy(() => import("./pages/admin_etablissement/ServicesScolairesAdminPage").then((m) => ({ default: m.ServicesScolairesAdminPage })));
const EvenementsAdminPage = lazy(() => import("./pages/admin_etablissement/EvenementsAdminPage").then((m) => ({ default: m.EvenementsAdminPage })));

const AdminMinisterielDashboard = lazy(() => import("./pages/admin_ministeriel/AdminMinisterielDashboard").then((m) => ({ default: m.AdminMinisterielDashboard })));
const EtablissementsPage = lazy(() => import("./pages/admin_ministeriel/EtablissementsPage").then((m) => ({ default: m.EtablissementsPage })));
const ReferentielsPage = lazy(() => import("./pages/admin_ministeriel/ReferentielsPage").then((m) => ({ default: m.ReferentielsPage })));
const UtilisateursMinisterielPage = lazy(() => import("./pages/admin_ministeriel/UtilisateursPage").then((m) => ({ default: m.UtilisateursPage })));
const ContenusPage = lazy(() => import("./pages/admin_ministeriel/ContenusPage").then((m) => ({ default: m.ContenusPage })));
const EvenementsSupervisionPage = lazy(() => import("./pages/admin_ministeriel/EvenementsSupervisionPage").then((m) => ({ default: m.EvenementsSupervisionPage })));
const IndicateursPage = lazy(() => import("./pages/admin_ministeriel/IndicateursPage").then((m) => ({ default: m.IndicateursPage })));
const JournalAuditPage = lazy(() => import("./pages/admin_ministeriel/JournalAuditPage").then((m) => ({ default: m.JournalAuditPage })));

const MessagerieListPage = lazy(() => import("./pages/messagerie/MessagerieListPage").then((m) => ({ default: m.MessagerieListPage })));
const ConversationPage = lazy(() => import("./pages/messagerie/ConversationPage").then((m) => ({ default: m.ConversationPage })));
const SignalementsPage = lazy(() => import("./pages/admin_etablissement/SignalementsPage").then((m) => ({ default: m.SignalementsPage })));
const AlertesElProfessorPage = lazy(() => import("./pages/admin_etablissement/AlertesElProfessorPage").then((m) => ({ default: m.AlertesElProfessorPage })));
const BilletteriePage = lazy(() => import("./pages/billetterie/BilletteriePage").then((m) => ({ default: m.BilletteriePage })));
const ValiderAccesPage = lazy(() => import("./pages/controle_acces/ValiderAccesPage").then((m) => ({ default: m.ValiderAccesPage })));
const MicroJobsPage = lazy(() => import("./pages/micro_jobs/MicroJobsPage").then((m) => ({ default: m.MicroJobsPage })));
const MicroJobsArbitragePage = lazy(() => import("./pages/admin_ministeriel/MicroJobsArbitragePage").then((m) => ({ default: m.MicroJobsArbitragePage })));
const MarketplacePage = lazy(() => import("./pages/eleve/MarketplacePage").then((m) => ({ default: m.MarketplacePage })));
const MarketplaceAdminPage = lazy(() => import("./pages/admin_etablissement/MarketplaceAdminPage").then((m) => ({ default: m.MarketplaceAdminPage })));
const MentionsLegalesPage = lazy(() => import("./pages/legal/MentionsLegalesPage").then((m) => ({ default: m.MentionsLegalesPage })));
const PolitiqueConfidentialitePage = lazy(() => import("./pages/legal/PolitiqueConfidentialitePage").then((m) => ({ default: m.PolitiqueConfidentialitePage })));
const CGUPage = lazy(() => import("./pages/legal/CGUPage").then((m) => ({ default: m.CGUPage })));
const PolitiqueCookiesPage = lazy(() => import("./pages/legal/PolitiqueCookiesPage").then((m) => ({ default: m.PolitiqueCookiesPage })));

/** Écran d’attente pendant le téléchargement d’une page (annoncé aux lecteurs d’écran). */
function ChargementPage() {
  return (
    <div className="page-content" role="status" aria-live="polite">
      <span className="sr-only">Chargement de la page…</span>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <ConfirmationProvider>
      <AuthProvider>
      <AccessibiliteProvider>
        <AppLayout>
          <Suspense fallback={<ChargementPage />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/etablissements" element={<EtablissementsAnnuairePage />} />
            <Route
              path="/cartes"
              element={
                <Suspense fallback={<div className="page-content" />}>
                  <CartesPage />
                </Suspense>
              }
            />
            <Route
              path="/connexion"
              element={
                <RedirectIfAuthenticated>
                  <LoginPage />
                </RedirectIfAuthenticated>
              }
            />
            <Route
              path="/inscription-tuteur"
              element={
                <RedirectIfAuthenticated>
                  <SignupPage role="tuteur" />
                </RedirectIfAuthenticated>
              }
            />
            <Route
              path="/inscription-enseignant"
              element={
                <RedirectIfAuthenticated>
                  <SignupPage role="enseignant" />
                </RedirectIfAuthenticated>
              }
            />
            <Route
              path="/mot-de-passe-oublie"
              element={
                <RedirectIfAuthenticated>
                  <MotDePasseOubliePage />
                </RedirectIfAuthenticated>
              }
            />
            <Route
              path="/changer-mot-de-passe"
              element={
                <RequireAuth>
                  <ChangePasswordPage />
                </RequireAuth>
              }
            />
            <Route path="/dashboard" element={<DashboardRedirect />} />
            <Route path="/mentions-legales" element={<MentionsLegalesPage />} />
            <Route path="/politique-confidentialite" element={<PolitiqueConfidentialitePage />} />
            <Route path="/cgu" element={<CGUPage />} />
            <Route path="/politique-cookies" element={<PolitiqueCookiesPage />} />

            {/* Tuteur */}
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
              path="/tuteur/services"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <TuteurServicesScolairesPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/vie-scolaire"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <VieScolaireEnfantPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/devoirs"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <DevoirsEnfantPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/marketplace"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <MarketplaceEnfantPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/cours-direct"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <SessionsLiveEnfantPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/el-professor"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <ElProfessorTuteurPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/el-professor-famille"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <ElProfessorTuteurPage ongletInitial="famille" />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/coffre-fort"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <CoffreFortPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/radar-familial"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <RadarFamilialPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/bulletins"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <BulletinsEnfantPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/alphabetisation"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <AlphabetisationPage />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/passeport"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <PasseportEnfantPage />
                </RequireAuth>
              }
            />

            {/* Eleve */}
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
              path="/eleve/cours/:coursId"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <CoursDetailPage />
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
            <Route
              path="/eleve/cours-direct"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <CoursDirectPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/services"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <EleveServicesScolairesPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/marketplace"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <MarketplacePage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/el-professor"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <ElProfessorElevePage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/el-professor-famille"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <ElProfessorElevePage ongletInitial="famille" />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/passeport"
              element={
                <RequireAuth roles={["eleve"]}>
                  <PasseportPage />
                </RequireAuth>
              }
            />

            {/* Enseignant */}
            <Route
              path="/enseignant"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <EnseignantDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/postes"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <PostesListPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/postes/:posteId/postuler"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <PostulerPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/candidatures"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesCandidaturesPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/contrats"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesContratsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/cours"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesCoursPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/devoirs"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesDevoirsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/cours-direct"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <SessionsLivePage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/salles"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesSallesPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/el-professor"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <ElProfessorPage />
                </RequireAuth>
              }
            />
            <Route
              path="/salle-live/:sessionId"
              element={
                <RequireAuth roles={["enseignant", "eleve"]}>
                  <SalleLivePage />
                </RequireAuth>
              }
            />

            {/* Admin etablissement (A+) */}
            <Route
              path="/admin-etablissement/a-traiter"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ATraiterEtablissementPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <AdminEtabDashboard />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/classes"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ClassesPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/inscriptions"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <InscriptionsAValiderPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/console"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ConsoleEtablissementPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/saisie-papier"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <SaisiePapierPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/rentree"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <RentreePage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/vie-scolaire"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <VieScolairePage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/vie-scolaire/:eleveUtilisateurId"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <VieScolairePage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/postes"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <RecrutementPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/contestations"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ContestationsPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/actes"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ActesAdminPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/referentiels"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ReferentielsEtabPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/services"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ServicesScolairesAdminPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/evenements"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <EvenementsAdminPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/marketplace"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <MarketplaceAdminPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />

            {/* Messagerie (tuteur, eleve, enseignant) */}
            <Route
              path="/messagerie"
              element={
                <RequireAuth roles={["tuteur", "eleve", "enseignant"]}>
                  <MessagerieListPage />
                </RequireAuth>
              }
            />
            <Route
              path="/messagerie/:conversationId"
              element={
                <RequireAuth roles={["tuteur", "eleve", "enseignant"]}>
                  <ConversationPage />
                </RequireAuth>
              }
            />

            {/* Billetterie (achat, tous roles consommateurs) */}
            <Route
              path="/billetterie"
              element={
                <RequireAuth roles={["tuteur", "eleve", "enseignant", "admin_etablissement"]}>
                  <BilletteriePage />
                </RequireAuth>
              }
            />

            {/* Controle d'acces (contrôleurs designes : enseignant ou admin etablissement) */}
            <Route
              path="/valider-acces"
              element={
                <RequireAuth roles={["enseignant", "admin_etablissement"]}>
                  <ValiderAccesPage />
                </RequireAuth>
              }
            />

            {/* Micro-jobs : publier/payer ouvert a tous les roles, accepter reserve aux non-eleves (verifie cote backend) */}
            <Route
              path="/micro-jobs"
              element={
                <RequireAuth roles={["enseignant", "tuteur", "admin_etablissement", "admin_ministeriel", "eleve"]}>
                  <MicroJobsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/micro-jobs-arbitrage"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <MicroJobsArbitragePage />
                </RequireAuth>
              }
            />

            {/* Admin etablissement (A+) — signalements messagerie */}
            <Route
              path="/admin-etablissement/signalements"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <SignalementsPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/alertes-el-professor"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <AlertesElProfessorPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />

            {/* Admin ministeriel (A++) */}
            <Route
              path="/admin-ministeriel/a-traiter"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <ATraiterPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <AdminMinisterielDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/etablissements"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <EtablissementsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/referentiels"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <ReferentielsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/utilisateurs"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <UtilisateursMinisterielPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/contenus"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <ContenusPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/evenements"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <EvenementsSupervisionPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/indicateurs"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <IndicateursPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/indicateurs"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <IndicateursPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/journal-audit"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <JournalAuditPage />
                </RequireAuth>
              }
            />

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
          </Suspense>
        </AppLayout>
      </AccessibiliteProvider>
      </AuthProvider>
      </ConfirmationProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
