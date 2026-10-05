import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { PublicLayout } from '@/components/layout/PublicLayout';
import { SpaceLayout } from '@/components/layout/SpaceLayout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { RouteFallback } from '@/components/RouteFallback';

/* Les pages publiques critiques sont chargées immédiatement (vitesse perçue),
   les espaces connectés et les pages secondaires sont découpés en morceaux. */
import HomePage from '@/pages/HomePage';

const ServicePage = lazy(() => import('@/pages/marketing/ServicePage'));
const HowItWorksPage = lazy(() => import('@/pages/marketing/HowItWorksPage'));
const TrustPage = lazy(() => import('@/pages/marketing/TrustPage'));
const PricingPage = lazy(() => import('@/pages/marketing/PricingPage'));
const ContactPage = lazy(() => import('@/pages/marketing/ContactPage'));
const RequestFormPage = lazy(() => import('@/pages/RequestFormPage'));
const RequestConfirmationPage = lazy(() => import('@/pages/RequestConfirmationPage'));
const CompaniesPage = lazy(() => import('@/pages/ecosystem/CompaniesPage'));
const CompanyPage = lazy(() => import('@/pages/ecosystem/CompanyPage'));
const RealizationsPage = lazy(() => import('@/pages/ecosystem/RealizationsPage'));
const RealizationPage = lazy(() => import('@/pages/ecosystem/RealizationPage'));
const OpportunitiesPage = lazy(() => import('@/pages/ecosystem/OpportunitiesPage'));
const OpportunityPage = lazy(() => import('@/pages/ecosystem/OpportunityPage'));
const CompanyOnboardingPage = lazy(() => import('@/pages/ecosystem/CompanyOnboardingPage'));
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'));
const PasswordResetPage = lazy(() => import('@/pages/auth/PasswordResetPage'));
const SpaceHomePage = lazy(() => import('@/pages/space/SpaceHomePage'));
const ProjectDetailPage = lazy(() => import('@/pages/space/ProjectDetailPage'));
const PropertiesPage = lazy(() => import('@/pages/space/PropertiesPage'));
const RequestsPage = lazy(() => import('@/pages/space/RequestsPage'));
const CompanySpacePage = lazy(() => import('@/pages/space/CompanySpacePage'));
const AdminSpacePage = lazy(() => import('@/pages/space/AdminSpacePage'));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));

export function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        {/* ------------------------------------------------------ site public */}
        <Route element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route path="services" element={<Navigate to="/#services" replace />} />
          <Route path="services/:slug" element={<ServicePage />} />
          <Route path="comment-ca-marche" element={<HowItWorksPage />} />
          <Route path="confiance" element={<TrustPage />} />
          <Route path="tarifs" element={<PricingPage />} />
          <Route path="contact" element={<ContactPage />} />

          <Route path="demande" element={<RequestFormPage />} />
          <Route path="demande/confirmation/:reference" element={<RequestConfirmationPage />} />

          <Route path="entreprises-btp" element={<CompaniesPage />} />
          <Route path="entreprises/:slug" element={<CompanyPage />} />
          <Route path="realisations" element={<RealizationsPage />} />
          <Route path="realisations/:slug" element={<RealizationPage />} />
          <Route path="opportunites" element={<OpportunitiesPage />} />
          <Route path="opportunites/:slug" element={<OpportunityPage />} />
          <Route path="espace-entreprise" element={<CompanyOnboardingPage />} />

          {/* ---------------------------------------------------- authentification */}
          <Route path="connexion" element={<LoginPage />} />
          <Route path="inscription" element={<RegisterPage />} />
          <Route path="mot-de-passe-oublie" element={<PasswordResetPage />} />

          <Route path="*" element={<NotFoundPage />} />
        </Route>

        {/* ------------------------------------------------------- espaces connectés */}
        <Route
          path="/espace"
          element={
            <ProtectedRoute>
              <SpaceLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<SpaceHomePage />} />
          <Route path="projets/:id" element={<ProjectDetailPage />} />
          <Route path="proprietes" element={<PropertiesPage />} />
          <Route path="demandes" element={<RequestsPage />} />
          <Route path="entreprise" element={<CompanySpacePage />} />
          <Route
            path="admin"
            element={
              <ProtectedRoute permission="MANAGE_PROJECT">
                <AdminSpacePage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/espace" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
